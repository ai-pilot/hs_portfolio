/**
 * Orient Express Chat Widget - Embed Script
 *
 * Add this to your website:
 * <script>
 *   window.ORIENT_EXPRESS_API = "https://your-backend-url.azurewebsites.net";
 * </script>
 * <script src="orient-express.iife.js"></script>
 * <link rel="stylesheet" href="orient-express.css">
 *
 * Or for development:
 * <script>
 *   window.ORIENT_EXPRESS_API = "http://localhost:8000";
 * </script>
 * <script src="orient-express.iife.js"></script>
 * <link rel="stylesheet" href="orient-express.css">
 */

(function () {
  // Auto-detect API base from script location if not set
  if (!window.ORIENT_EXPRESS_API) {
    const scripts = document.getElementsByTagName("script");
    const currentScript = scripts[scripts.length - 1];
    const src = currentScript.src;
    if (src) {
      const url = new URL(src);
      window.ORIENT_EXPRESS_API = url.origin;
    } else {
      window.ORIENT_EXPRESS_API = "";
    }
  }

  // Create mount point if not exists
  if (!document.getElementById("orient-express-root")) {
    const div = document.createElement("div");
    div.id = "orient-express-root";
    document.body.appendChild(div);
  }
})();
