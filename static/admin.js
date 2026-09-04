/* Shared admin helpers: toasts + a small fetch wrapper.
   Replaces the alert()/window.location.reload() pattern the pages used before. */

(function () {
    'use strict';

    function toast(message, kind) {
        var area = document.getElementById('toast-area');
        if (!area) {
            window.alert(message);
            return;
        }

        var el = document.createElement('div');
        el.className = 'toast-msg toast-msg--' + (kind || 'ok');
        el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
        el.textContent = message;
        area.appendChild(el);

        window.setTimeout(function () { el.remove(); }, 4000);
    }

    /**
     * POST and parse JSON, surfacing HTTP and application-level errors the
     * same way. The old code called response.json() unconditionally, so a 500
     * that returned an HTML error page threw an opaque JSON parse error.
     */
    function postJSON(url, body, options) {
        var opts = { method: 'POST' };

        if (body instanceof FormData) {
            opts.body = body;
        } else if (body !== undefined) {
            opts.headers = { 'Content-Type': 'application/json' };
            opts.body = JSON.stringify(body);
        }

        return fetch(url, Object.assign(opts, options || {}))
            .then(function (response) {
                return response.text().then(function (text) {
                    var data;
                    try {
                        data = text ? JSON.parse(text) : {};
                    } catch (e) {
                        throw new Error('Server error (' + response.status + ')');
                    }
                    if (!response.ok || data.success === false) {
                        throw new Error(data.message || 'Request failed (' + response.status + ')');
                    }
                    return data;
                });
            });
    }

    /** Disable a submit button while its request is in flight. */
    function busy(button, isBusy, label) {
        if (!button) return;
        if (isBusy) {
            button.dataset.label = button.textContent;
            button.disabled = true;
            button.textContent = label || 'Working...';
        } else {
            button.disabled = false;
            button.textContent = button.dataset.label || button.textContent;
        }
    }

    window.Admin = { toast: toast, postJSON: postJSON, busy: busy };
})();
