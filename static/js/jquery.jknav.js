jQuery.uaMatch = function( ua ) {
    ua = ua.toLowerCase();
    var match = /(chrome)[ \/]([\w.]+)/.exec( ua ) ||
        /(webkit)[ \/]([\w.]+)/.exec( ua ) ||
        /(opera)(?:.*version|)[ \/]([\w.]+)/.exec( ua ) ||
        /(msie) ([\w.]+)/.exec( ua ) ||
        ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec( ua ) || [];
    return {
        browser: match[ 1 ] || "",
        version: match[ 2 ] || "0"
    };
};
if ( !jQuery.browser ) {
    var 
    matched = jQuery.uaMatch( navigator.userAgent ),
    browser = {};
    if ( matched.browser ) {
        browser[ matched.browser ] = true;
        browser.version = matched.version;
    }
    // Chrome is Webkit, but Webkit is also Safari.
    if ( browser.chrome ) {
        browser.webkit = true;
    } else if ( browser.webkit ) {
        browser.safari = true;
    }
    jQuery.browser = browser;
}


/**
 * @preserve jknav
 * @name      jquery.jknav.js
 * @author    Yu-Jie Lin http://j.mp/Google-livibetter
 * @version   0.5.0.1
 * @date      05-24-2011
 * @copyright (c) 2010, 2011 Yu-Jie Lin <livibetter@gmail.com>
 * @license   BSD License
 * @homepage  http://code.google.com/p/lilbtn/wiki/JsJqueryJknav
 * @example   http://lilbtn.googlecode.com/hg/src/static/js/jquery/jquery.jknav.demo.html
*/
(function ($) {
    /**
     * Print out debug infomation via console object
     * @param {String} debug information
     */
    function log (message) {
        var console = window.console;
        if ($.jknav.DEBUG && console && console.log)
            console.log('jknav: ' + message);
        }

    /**
     * Add jQuery objects to navgation list
     *
     * @param {Function} callback Callback function to be invoked after plugin scroll to item
     * @param {String} name Navagation set name
     * @return {jQuery} <code>this</code> for chaining
     */
    $.fn.jknav = function (callback, name) {
        if (name == null)
            name = 'default';
        if ($.jknav.items[name] == null)
            $.jknav.items[name] = [];
        return this.each(function () {
            $.jknav.items[name].push([this, callback]);
            $.jknav.items[name].sort(function (a, b) {
                var a_top = $(a[0]).offset().top;
                var b_top = $(b[0]).offset().top;
                if (a_top < b_top)
                    return -1;
                if (a_top > b_top)
                    return 1;
                if (a_top == b_top) {
                    var a_left = $(a[0]).offset().left;
                    var b_left = $(b[0]).offset().left;
                    if (a_left < b_left)
                        return -1;
                    if (a_left > b_left)
                        return 1;
                    return 0;
                    }
                });
            });
        };

    /**
     * A helper to do callback
     * @param {Number} index of the item navgation set
     * @param {Object} opts Options
     */
    function do_callback(index, opts) {
        var callback = $.jknav.items[opts.name][index][1];
        if (callback)
            callback($.jknav.items[opts.name][index][0]);
        }

    /**
     * Calculate the index of next item
     * @param {Number} offset Indicates move forword or backward
     * @param {Object} opts Options
     */
    function calc_index(offset, opts) {
        var index = $.jknav.index[opts.name];
        log('Calculating index for ' + opts.name + ', current index = ' + index);
        if (index == null) {
            // Initialize index
            var top = $($.jknav.TARGET).scrollTop();
            log($.jknav.TARGET + ' top = ' + top);
            $.each($.jknav.items[opts.name], function (idx, item) {
                // Got a strange case: top = 180, item_top = 180.35...
                var item_top = Math.floor($(item).offset().top);
                if (top >= item_top)
                    index = idx;
                });
            if (index == null) {
                if (offset > 0)
                    index = 0
                else
                    index = $.jknav.items[opts.name].length - 1;
                }
            else {
                if (offset > 0 && ++index >= $.jknav.items[opts.name].length)
                    index = 0
                else if (offset < 0 && top == Math.floor($($.jknav.items[opts.name][index]).offset().top) && --index < 0)
                    index = $.jknav.items[opts.name].length - 1;
                }
            }
        else {
            if (!opts.circular && ((index == 0 && offset == -1) || (index == $.jknav.items[opts.name].length - 1 && offset == 1)))
                return index;
            index += offset;
            if (index >= $.jknav.items[opts.name].length)
                index = 0;
            if (index < 0)
                index = $.jknav.items[opts.name].length - 1;
            }
        log('new index = ' + index);
        $.jknav.index[opts.name] = index;
        return index;
        }
        
    /**
     * Keyup handler
     * @param {Event} e jQuery event object
     * @param {Object} opts Options
     */
    function keyup(e, opts) {
        if (e.target.tagName.toLowerCase() == 'input' ||
          e.target.tagName.toLowerCase() == 'button' ||
          e.target.tagName.toLowerCase() == 'select' ||
          e.target.tagName.toLowerCase() == 'textarea') {
            log('keyup: ' + e.target.tagName + ', target is INPUT ignored.');
            return
            }
        var ch = String.fromCharCode(e.keyCode).toLowerCase();
        log('keyup: ' + e.target.tagName + ', key: ' + ch);
        if (ch == opts.up.toLowerCase() || ch == opts.down.toLowerCase()) {
            if (opts.reevaluate)
                $.jknav.index[opts.name] = null;
            var index = calc_index((ch == opts.down.toLowerCase()) ? 1 : -1, opts);
            var $item = $($.jknav.items[opts.name][index][0]);
            $($.jknav.TARGET).animate(
                {
                    scrollLeft: Math.floor($item.offset().left),
                    scrollTop: Math.floor($item.offset().top)
                    },
                opts.speed,
                opts.easing,
                function () {
                    do_callback(index, opts)
                    }
                );
            }
        }

    $.jknav = {
        index: {},
        items: {},
        opts: {},
        default_options: {
            up: 'k',
            down: 'j',
            name: 'default',
            easing: 'swing',
            speed: 'normal',
            circular: true,
            reevaluate: false
            },
        DEBUG: false,
        TARGET_KEYUP: 'html',
        // IE, Firefox, and Opera must use <html> to scroll
        // Webkit must use <bod> to scroll
        TARGET: (!$.browser.webkit)?'html':'body',
        /**
         * Initialization function
         * @param {Object} options Options
         */
        init: function (options) {
            var opts = $.extend($.extend({}, $.jknav.default_options), options);
            $.jknav.index[opts.name] = null;
            $.jknav.opts[opts.name] = opts;
            $($.jknav.TARGET_KEYUP).keyup(function (e) {
                keyup(e, opts);
                });
            log('new set "' + opts.name + '" initialzed.');
            },
        /**
         * Navigate up
         * @param {String} name name of set
         */
        up: function (name) {
            var opts = $.jknav.opts[name || 'default'];
            keyup({target: {tagName: ''}, keyCode: opts.up.charCodeAt(0)}, opts);
            },
        /**
         * Navigate down
         * @param {String} name name of set
         */
        down: function (name) {
            var opts = $.jknav.opts[name || 'default'];
            keyup({target: {tagName: ''}, keyCode: opts.down.charCodeAt(0)}, opts);
            }
        };
    })(jQuery);
// vim: ts=2: sw=2