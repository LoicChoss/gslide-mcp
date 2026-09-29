/**
 * Cross-deck slide copy via SlidesApp.appendSlide().
 *
 * The Slides REST API has NO cross-presentation copy. Apps Script's
 * SlidesApp.appendSlide(slide) does — it carries layout, theme, fonts,
 * images, and styling. This web app exposes that as an HTTP endpoint the
 * gslides MCP can call.
 *
 * Deployment (one-time):
 *   1. Open https://script.google.com → New project → name it
 *      "gslides-mcp cross-deck copy".
 *   2. Paste this entire file as Code.gs (replace the default).
 *   3. Project Settings → enable Slides API and Drive API (advanced services).
 *   4. Deploy → New deployment → type: Web app.
 *      - Execute as: Me (your account).
 *      - Who has access: Anyone (or "Anyone with Google account" if you
 *        prefer a softer scope; the URL is unguessable).
 *   5. Authorize when prompted.
 *   6. Copy the deployed URL (`/macros/s/AKfycbx.../exec`).
 *   7. Save it to `~/.gslides-mcp/appscript_url` (one-line text file) OR
 *      export `GSLIDES_MCP_APPSCRIPT_URL=...` before launching the MCP.
 *
 * Subsequent edits to this file: re-deploy via Manage Deployments → edit →
 * new version. The URL stays the same.
 *
 * Hosted, multi-user server (GSLIDES_MCP_TRANSPORT=http): deploy as an
 * API executable instead, so each copy runs as the signed-in user:
 *   1. Project Settings → Google Cloud Platform (GCP) project → Change
 *      project → the number of the project that holds the server's OAuth
 *      client (the Apps Script API must be enabled there).
 *   2. Deploy → New deployment → type: API executable → Who has access:
 *      Anyone within <your domain>.
 *   3. Project Settings → copy the Script ID and set
 *      GSLIDES_MCP_APPSCRIPT_ID=<script id> on the server.
 * The server then calls api() through scripts.run with the user's token.
 */

var VERSION = "0.5";

// Successful copy results are remembered for this long, keyed by the
// caller's requestId, so a replayed request returns the same answer.
var REPLAY_CACHE_SECONDS = 21600; // 6h, the CacheService maximum

/**
 * Entry point for scripts.run (API executable). Same ops as doPost, but the
 * result is returned as-is and the script runs as the calling user.
 */
function api(body) {
  body = body || {};
  var op = body.op || "copy";
  if (op === "copy") {
    return _replaySafe_(body.requestId, function () {
      return copySlide_(body);
    });
  } else if (op === "ping") {
    return {ok: true, version: VERSION};
  }
  throw new Error("unknown op: " + op);
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents || "{}");
    var op = body.op || "copy";
    if (op === "copy") {
      return _json(_replaySafe_(body.requestId, function () {
        return copySlide_(body);
      }));
    } else if (op === "ping") {
      return _json({ok: true, version: VERSION});
    } else {
      return _json({error: "unknown op: " + op}, 400);
    }
  } catch (err) {
    // Do not reflect err.stack — when this web app is deployed "Anyone",
    // any caller could probe it with malformed input and harvest script
    // internals via the response.
    return _json({error: String(err)}, 500);
  }
}

/**
 * Run `fn` at most once per requestId.
 *
 * Google's response relay (script.googleusercontent.com) sometimes 404s a
 * result this script already produced. The MCP then replays the POST with
 * the same requestId; answering from cache keeps the slide from being
 * appended twice. Requests without a requestId (pre-0.4 clients) run as-is.
 */
function _replaySafe_(requestId, fn) {
  if (!requestId) {
    return fn();
  }
  var key = "req:" + String(requestId).slice(0, 64);
  var cache = CacheService.getUserCache();
  var lock = LockService.getUserLock(); // per user: one person's copies queue, not the team's
  lock.waitLock(60000); // a replay may arrive while the first run is still going
  try {
    var hit = cache.get(key);
    if (hit) {
      return JSON.parse(hit);
    }
    var result = fn(); // errors propagate uncached: nothing was appended
    cache.put(key, JSON.stringify(result), REPLAY_CACHE_SECONDS);
    return result;
  } finally {
    lock.releaseLock();
  }
}

/**
 * Copy ONE slide from src to dst.
 *
 * @param {Object} req
 *   - srcId: source presentation ID
 *   - dstId: destination presentation ID
 *   - srcSlide: 1-based index OR objectId of slide to copy from src
 *   - insertionIndex: optional 0-based insertion index in dst (default = end)
 *
 * @return {Object} {newSlideId, dstIndex}
 */
function copySlide_(req) {
  var src = SlidesApp.openById(req.srcId);
  var dst = SlidesApp.openById(req.dstId);
  var srcSlide = _resolveSlide_(src, req.srcSlide);
  if (!srcSlide) {
    throw new Error("src slide not found: " + req.srcSlide);
  }

  var newSlide;
  var newIndex;
  if (typeof req.insertionIndex === "number") {
    newSlide = dst.insertSlide(req.insertionIndex, srcSlide);
    newIndex = req.insertionIndex;
  } else {
    // appendSlide: the new slide goes to the end.
    var existingCount = dst.getSlides().length;
    newSlide = dst.appendSlide(srcSlide);
    newIndex = existingCount;
  }

  // Apps Script auto-saves at script exit — no saveAndClose() + openById()
  // round-trip needed. Earlier versions did that and burned ~10-20s per
  // call; dropped after timeout regressions in high-slide-count workflows.
  return {newSlideId: newSlide.getObjectId(), dstIndex: newIndex};
}

function _resolveSlide_(presentation, ref) {
  // Numeric ref → 1-based index
  if (typeof ref === "number" || /^\d+$/.test(String(ref))) {
    var idx = parseInt(ref, 10) - 1;
    var slides = presentation.getSlides();
    return slides[idx] || null;
  }
  // String ref → objectId
  var slides = presentation.getSlides();
  for (var i = 0; i < slides.length; i++) {
    if (slides[i].getObjectId() === ref) {
      return slides[i];
    }
  }
  return null;
}

function _json(payload, status) {
  // Note: ContentService has no HTTP-status API; the `status` param is accepted
  // for caller intent but ignored. Errors are conveyed via the JSON body.
  var out = ContentService.createTextOutput(JSON.stringify(payload));
  out.setMimeType(ContentService.MimeType.JSON);
  return out;
}
