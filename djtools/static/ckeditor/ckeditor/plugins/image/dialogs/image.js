﻿/*
 Copyright (c) 2003-2015, CKSource - Frederico Knabben. All rights reserved.
 For licensing, see LICENSE.md or http://ckeditor.com/license
*/
(function() {
    var v = function(d, l) {
        function v() {
            var a = arguments,
                b = this.getContentElement("advanced", "txtdlgGenStyle");
            b && b.commit.apply(b, a);
            this.foreach(function(b) {
                b.commit && "txtdlgGenStyle" != b.id && b.commit.apply(b, a)
            })
        }

        function k(a) {
            if (!w) {
                w = 1;
                var b = this.getDialog(),
                    c = b.imageElement;
                if (c) {
                    this.commit(1, c);
                    a = [].concat(a);
                    for (var d = a.length, f, g = 0; g < d; g++)(f = b.getContentElement.apply(b, a[g].split(":"))) && f.setup(1, c)
                }
                w = 0
            }
        }
        var m = /^\s*(\d+)((px)|\%)?\s*$/i,
            z = /(^\s*(\d+)((px)|\%)?\s*$)|^$/i,
            r = /^\d+px$/,
            A = function() {
                var a = this.getValue(),
                    b = this.getDialog(),
                    c = a.match(m);
                c && ("%" == c[2] && n(b, !1), a = c[1]);
                b.lockRatio && (c = b.originalElement, "true" == c.getCustomData("isReady") && ("txtHeight" == this.id ? (a && "0" != a && (a = Math.round(a / c.$.height * c.$.width)), isNaN(a) || b.setValueOf("info", "txtWidth", a)) : (a && "0" != a && (a = Math.round(a / c.$.width * c.$.height)), isNaN(a) || b.setValueOf("info", "txtHeight", a))));
                e(b)
            },
            e = function(a) {
                if (!a.originalElement || !a.preview) return 1;
                a.commitContent(4, a.preview);
                return 0
            },
            w, n = function(a,
                b) {
                if (!a.getContentElement("info", "ratioLock")) return null;
                var c = a.originalElement;
                if (!c) return null;
                if ("check" == b) {
                    if (!a.userlockRatio && "true" == c.getCustomData("isReady")) {
                        var d = a.getValueOf("info", "txtWidth"),
                            f = a.getValueOf("info", "txtHeight"),
                            c = 1E3 * c.$.width / c.$.height,
                            g = 1E3 * d / f;
                        a.lockRatio = !1;
                        d || f ? isNaN(c) || isNaN(g) || Math.round(c) != Math.round(g) || (a.lockRatio = !0) : a.lockRatio = !0
                    }
                } else void 0 !== b ? a.lockRatio = b : (a.userlockRatio = 1, a.lockRatio = !a.lockRatio);
                d = CKEDITOR.document.getById(t);
                a.lockRatio ?
                    d.removeClass("cke_btn_unlocked") : d.addClass("cke_btn_unlocked");
                d.setAttribute("aria-checked", a.lockRatio);
                CKEDITOR.env.hc && d.getChild(0).setHtml(a.lockRatio ? CKEDITOR.env.ie ? "■" : "▣" : CKEDITOR.env.ie ? "□" : "▢");
                return a.lockRatio
            },
            B = function(a, b) {
                var c = a.originalElement;
                if ("true" == c.getCustomData("isReady")) {
                    var d = a.getContentElement("info", "txtWidth"),
                        f = a.getContentElement("info", "txtHeight"),
                        g;
                    b ? c = g = 0 : (g = c.$.width, c = c.$.height);
                    d && d.setValue(g);
                    f && f.setValue(c)
                }
                e(a)
            },
            C = function(a, b) {
                function c(a, b) {
                    var c =
                        a.match(m);
                    return c ? ("%" == c[2] && (c[1] += "%", n(d, !1)), c[1]) : b
                }
                if (1 == a) {
                    var d = this.getDialog(),
                        f = "",
                        g = "txtWidth" == this.id ? "width" : "height",
                        e = b.getAttribute(g);
                    e && (f = c(e, f));
                    f = c(b.getStyle(g), f);
                    this.setValue(f)
                }
            },
            x, u = function() {
                var a = this.originalElement,
                    b = CKEDITOR.document.getById(p);
                a.setCustomData("isReady", "true");
                a.removeListener("load", u);
                a.removeListener("error", h);
                a.removeListener("abort", h);
                b && b.setStyle("display", "none");
                this.dontResetSize || B(this, !1 === d.config.image_prefillDimensions);
                this.firstLoad &&
                    CKEDITOR.tools.setTimeout(function() {
                        n(this, "check")
                    }, 0, this);
                this.dontResetSize = this.firstLoad = !1;
                e(this)
            },
            h = function() {
                var a = this.originalElement,
                    b = CKEDITOR.document.getById(p);
                a.removeListener("load", u);
                a.removeListener("error", h);
                a.removeListener("abort", h);
                a = CKEDITOR.getUrl(CKEDITOR.plugins.get("image").path + "images/noimage.png");
                this.preview && this.preview.setAttribute("src", a);
                b && b.setStyle("display", "none");
                n(this, !1)
            },
            q = function(a) {
                return CKEDITOR.tools.getNextId() + "_" + a
            },
            t = q("btnLockSizes"),
            y = q("btnResetSize"),
            p = q("ImagePreviewLoader"),
            E = q("previewLink"),
            D = q("previewImage");
        return {
            title: d.lang.image["image" == l ? "title" : "titleButton"],
            minWidth: 420,
            minHeight: 360,
            onShow: function() {
                this.linkEditMode = this.imageEditMode = this.linkElement = this.imageElement = !1;
                this.lockRatio = !0;
                this.userlockRatio = 0;
                this.dontResetSize = !1;
                this.firstLoad = !0;
                this.addLink = !1;
                var a = this.getParentEditor(),
                    b = a.getSelection(),
                    c = (b = b && b.getSelectedElement()) && a.elementPath(b).contains("a", 1),
                    d = CKEDITOR.document.getById(p);
                d && d.setStyle("display", "none");
                x = new CKEDITOR.dom.element("img", a.document);
                this.preview = CKEDITOR.document.getById(D);
                this.originalElement = a.document.createElement("img");
                this.originalElement.setAttribute("alt", "");
                this.originalElement.setCustomData("isReady", "false");
                c && (this.linkElement = c, this.addLink = this.linkEditMode = !0, a = c.getChildren(), 1 == a.count() && (d = a.getItem(0), d.type == CKEDITOR.NODE_ELEMENT && (d.is("img") || d.is("input")) && (this.imageElement = a.getItem(0), this.imageElement.is("img") ? this.imageEditMode =
                    "img" : this.imageElement.is("input") && (this.imageEditMode = "input"))), "image" == l && this.setupContent(2, c));
                if (this.customImageElement) this.imageEditMode = "img", this.imageElement = this.customImageElement, delete this.customImageElement;
                else if (b && "img" == b.getName() && !b.data("cke-realelement") || b && "input" == b.getName() && "image" == b.getAttribute("type")) this.imageEditMode = b.getName(), this.imageElement = b;
                this.imageEditMode && (this.cleanImageElement = this.imageElement, this.imageElement = this.cleanImageElement.clone(!0, !0), this.setupContent(1, this.imageElement));
                n(this, !0);
                CKEDITOR.tools.trim(this.getValueOf("info", "txtUrl")) || (this.preview.removeAttribute("src"), this.preview.setStyle("display", "none"))
            },
            onOk: function() {
                if (this.imageEditMode) {
                    var a = this.imageEditMode;
                    "image" == l && "input" == a && confirm(d.lang.image.button2Img) ? (this.imageElement = d.document.createElement("img"), this.imageElement.setAttribute("alt", ""), d.insertElement(this.imageElement)) : "image" != l && "img" == a && confirm(d.lang.image.img2Button) ? (this.imageElement =
                        d.document.createElement("input"), this.imageElement.setAttributes({
                            type: "image",
                            alt: ""
                        }), d.insertElement(this.imageElement)) : (this.imageElement = this.cleanImageElement, delete this.cleanImageElement)
                } else "image" == l ? this.imageElement = d.document.createElement("img") : (this.imageElement = d.document.createElement("input"), this.imageElement.setAttribute("type", "image")), this.imageElement.setAttribute("alt", "");
                this.linkEditMode || (this.linkElement = d.document.createElement("a"));
                this.commitContent(1, this.imageElement);
                this.commitContent(2, this.linkElement);
                this.imageElement.getAttribute("style") || this.imageElement.removeAttribute("style");
                this.imageEditMode ? !this.linkEditMode && this.addLink ? (d.insertElement(this.linkElement), this.imageElement.appendTo(this.linkElement)) : this.linkEditMode && !this.addLink && (d.getSelection().selectElement(this.linkElement), d.insertElement(this.imageElement)) : this.addLink ? this.linkEditMode ? this.linkElement.equals(d.getSelection().getSelectedElement()) ? (this.linkElement.setHtml(""), this.linkElement.append(this.imageElement, !1)) : d.insertElement(this.imageElement) : (d.insertElement(this.linkElement), this.linkElement.append(this.imageElement, !1)) : d.insertElement(this.imageElement)
            },
            onLoad: function() {
                "image" != l && this.hidePage("Link");
                var a = this._.element.getDocument();
                this.getContentElement("info", "ratioLock") && (this.addFocusable(a.getById(y), 5), this.addFocusable(a.getById(t), 5));
                this.commitContent = v
            },
            onHide: function() {
                this.preview && this.commitContent(8, this.preview);
                this.originalElement && (this.originalElement.removeListener("load",
                    u), this.originalElement.removeListener("error", h), this.originalElement.removeListener("abort", h), this.originalElement.remove(), this.originalElement = !1);
                delete this.imageElement
            },
            contents: [{
                id: "info",
                label: d.lang.image.infoTab,
                accessKey: "I",
                elements: [{
                    type: "vbox",
                    padding: 0,
                    children: [{
                        type: "hbox",
                        widths: ["280px", "110px"],
                        align: "right",
                        children: [{
                            id: "txtUrl",
                            type: "text",
                            label: d.lang.common.url,
                            style: "display:none;",
                            required: !0,
                            onChange: function() {
                                var a = this.getDialog(),
                                    b = this.getValue();
                                if (0 < b.length) {
                                    var a = this.getDialog(),
                                        c = a.originalElement;
                                    a.preview && a.preview.removeStyle("display");
                                    c.setCustomData("isReady", "false");
                                    var d = CKEDITOR.document.getById(p);
                                    d && d.setStyle("display", "");
                                    c.on("load", u, a);
                                    c.on("error", h, a);
                                    c.on("abort", h, a);
                                    c.setAttribute("src", b);
                                    a.preview && (x.setAttribute("src", b), a.preview.setAttribute("src", x.$.src), e(a))
                                } else a.preview && (a.preview.removeAttribute("src"), a.preview.setStyle("display", "none"))
                            },
                            setup: function(a, b) {
                                if (1 == a) {
                                    var c = b.data("cke-saved-src") || b.getAttribute("src");
                                    this.getDialog().dontResetSize = !0;
                                    this.setValue(c);
                                    this.setInitValue()
                                }
                            },
                            commit: function(a, b) {
                                1 == a && (this.getValue() || this.isChanged()) ? (b.data("cke-saved-src", this.getValue()), b.setAttribute("src", this.getValue())) : 8 == a && (b.setAttribute("src", ""), b.removeAttribute("src"))
                            },
                            validate: CKEDITOR.dialog.validate.notEmpty(d.lang.image.urlMissing)
                        }, {
                            type: "button",
                            id: "browse",
                            style: "display:inline-block;margin-top:14px;",
                            align: "center",
                            label: d.lang.common.browseServer,
                            hidden: !0,
                            filebrowser: "info:txtUrl"
                        }]
                    }]
                }, {
                    type: "hbox",
                    children: [{
                        id: "basic",
                        type: "vbox",
                        children: [{
                            type: "hbox",
                            requiredContent: "img{width,height}",
                            widths: ["50%", "50%"],
                            children: [{
                                type: "vbox",
                                padding: 1,
                                children: [{
                                    type: "text",
                                    width: "45px",
                                    id: "txtWidth",
                                    label: d.lang.common.width,
                                    onKeyUp: A,
                                    onChange: function() {
                                        k.call(this, "advanced:txtdlgGenStyle")
                                    },
                                    validate: function() {
                                        var a = this.getValue().match(z);
                                        (a = !(!a || 0 === parseInt(a[1], 10))) || alert(d.lang.common.invalidWidth);
                                        return a
                                    },
                                    setup: C,
                                    commit: function(a, b) {
                                        var c = this.getValue();
                                        1 == a ? (c && d.activeFilter.check("img{width,height}") ? b.setStyle("width", CKEDITOR.tools.cssLength(c)) : b.removeStyle("width"), b.removeAttribute("width")) : 4 == a ? c.match(m) ? b.setStyle("width", CKEDITOR.tools.cssLength(c)) :
                                            (c = this.getDialog().originalElement, "true" == c.getCustomData("isReady") && b.setStyle("width", c.$.width + "px")) : 8 == a && (b.removeAttribute("width"), b.removeStyle("width"))
                                    }
                                }, {
                                    type: "text",
                                    id: "txtHeight",
                                    width: "45px",
                                    label: d.lang.common.height,
                                    onKeyUp: A,
                                    onChange: function() {
                                        k.call(this, "advanced:txtdlgGenStyle")
                                    },
                                    validate: function() {
                                        var a = this.getValue().match(z);
                                        (a = !(!a || 0 === parseInt(a[1], 10))) || alert(d.lang.common.invalidHeight);
                                        return a
                                    },
                                    setup: C,
                                    commit: function(a, b) {
                                        var c = this.getValue();
                                        1 == a ? (c && d.activeFilter.check("img{width,height}") ?
                                            b.setStyle("height", CKEDITOR.tools.cssLength(c)) : b.removeStyle("height"), b.removeAttribute("height")) : 4 == a ? c.match(m) ? b.setStyle("height", CKEDITOR.tools.cssLength(c)) : (c = this.getDialog().originalElement, "true" == c.getCustomData("isReady") && b.setStyle("height", c.$.height + "px")) : 8 == a && (b.removeAttribute("height"), b.removeStyle("height"))
                                    }
                                }]
                            }, {
                                id: "ratioLock",
                                type: "html",
                                style: "margin-top:30px;width:40px;height:40px;",
                                onLoad: function() {
                                    var a = CKEDITOR.document.getById(y),
                                        b = CKEDITOR.document.getById(t);
                                    a && (a.on("click", function(a) {
                                        B(this);
                                        a.data && a.data.preventDefault()
                                    }, this.getDialog()), a.on("mouseover", function() {
                                        this.addClass("cke_btn_over")
                                    }, a), a.on("mouseout", function() {
                                        this.removeClass("cke_btn_over")
                                    }, a));
                                    b && (b.on("click", function(a) {
                                            n(this);
                                            var b = this.originalElement,
                                                d = this.getValueOf("info", "txtWidth");
                                            "true" == b.getCustomData("isReady") && d && (b = b.$.height / b.$.width * d, isNaN(b) || (this.setValueOf("info", "txtHeight", Math.round(b)), e(this)));
                                            a.data && a.data.preventDefault()
                                        }, this.getDialog()),
                                        b.on("mouseover", function() {
                                            this.addClass("cke_btn_over")
                                        }, b), b.on("mouseout", function() {
                                            this.removeClass("cke_btn_over")
                                        }, b))
                                },
                                html: '\x3cdiv\x3e\x3ca href\x3d"javascript:void(0)" tabindex\x3d"-1" title\x3d"' + d.lang.image.lockRatio + '" class\x3d"cke_btn_locked" id\x3d"' + t + '" role\x3d"checkbox"\x3e\x3cspan class\x3d"cke_icon"\x3e\x3c/span\x3e\x3cspan class\x3d"cke_label"\x3e' + d.lang.image.lockRatio + '\x3c/span\x3e\x3c/a\x3e\x3ca href\x3d"javascript:void(0)" tabindex\x3d"-1" title\x3d"' + d.lang.image.resetSize +
                                    '" class\x3d"cke_btn_reset" id\x3d"' + y + '" role\x3d"button"\x3e\x3cspan class\x3d"cke_label"\x3e' + d.lang.image.resetSize + "\x3c/span\x3e\x3c/a\x3e\x3c/div\x3e"
                            }]
                        }, {
                            type: "vbox",
                            padding: 1,
                            children: [{
                                type: "text",
                                id: "txtBorder",
                                requiredContent: "img{border-width}",
                                width: "60px",
                                label: d.lang.image.border,
                                "default": "",
                                onKeyUp: function() {
                                    e(this.getDialog())
                                },
                                onChange: function() {
                                    k.call(this, "advanced:txtdlgGenStyle")
                                },
                                validate: CKEDITOR.dialog.validate.integer(d.lang.image.validateBorder),
                                setup: function(a, b) {
                                    if (1 ==
                                        a) {
                                        var c;
                                        c = (c = (c = b.getStyle("border-width")) && c.match(/^(\d+px)(?: \1 \1 \1)?$/)) && parseInt(c[1], 10);
                                        isNaN(parseInt(c, 10)) && (c = b.getAttribute("border"));
                                        this.setValue(c)
                                    }
                                },
                                commit: function(a, b) {
                                    var c = parseInt(this.getValue(), 10);
                                    1 == a || 4 == a ? (isNaN(c) ? !c && this.isChanged() && b.removeStyle("border") : (b.setStyle("border-width", CKEDITOR.tools.cssLength(c)), b.setStyle("border-style", "solid")), 1 == a && b.removeAttribute("border")) : 8 == a && (b.removeAttribute("border"), b.removeStyle("border-width"), b.removeStyle("border-style"),
                                        b.removeStyle("border-color"))
                                }
                            }]
                        }]
                    }, {
                        type: "vbox",
                        height: "250px",
                        children: [{
                            type: "html",
                            id: "htmlPreview",
                            style: "width:95%;",
                            html: "\x3cdiv\x3e" + CKEDITOR.tools.htmlEncode(d.lang.common.preview) + '\x3cbr\x3e\x3cdiv id\x3d"' + p + '" class\x3d"ImagePreviewLoader" style\x3d"display:none"\x3e\x3cdiv class\x3d"loading"\x3e\x26nbsp;\x3c/div\x3e\x3c/div\x3e\x3cdiv class\x3d"ImagePreviewBox"\x3e\x3ctable\x3e\x3ctr\x3e\x3ctd\x3e\x3ca href\x3d"javascript:void(0)" target\x3d"_blank" onclick\x3d"return false;" id\x3d"' +
                                E + '"\x3e\x3cimg id\x3d"' + D + '" alt\x3d"" /\x3e\x3c/a\x3e' + (d.config.image_previewText || "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Maecenas feugiat consequat diam. Maecenas metus. Vivamus diam purus, cursus a, commodo non, facilisis vitae, nulla. Aenean dictum lacinia tortor. Nunc iaculis, nibh non iaculis aliquam, orci felis euismod neque, sed ornare massa mauris sed velit. Nulla pretium mi et risus. Fusce mi pede, tempor id, cursus ac, ullamcorper nec, enim. Sed tortor. Curabitur molestie. Duis velit augue, condimentum at, ultrices a, luctus ut, orci. Donec pellentesque egestas eros. Integer cursus, augue in cursus faucibus, eros pede bibendum sem, in tempus tellus justo quis ligula. Etiam eget tortor. Vestibulum rutrum, est ut placerat elementum, lectus nisl aliquam velit, tempor aliquam eros nunc nonummy metus. In eros metus, gravida a, gravida sed, lobortis id, turpis. Ut ultrices, ipsum at venenatis fringilla, sem nulla lacinia tellus, eget aliquet turpis mauris non enim. Nam turpis. Suspendisse lacinia. Curabitur ac tortor ut ipsum egestas elementum. Nunc imperdiet gravida mauris.") +
                                "\x3c/td\x3e\x3c/tr\x3e\x3c/table\x3e\x3c/div\x3e\x3c/div\x3e"
                        }]
                    }]
                }]
            }]
        }
    };
    CKEDITOR.dialog.add("image", function(d) {
        return v(d, "image")
    });
    CKEDITOR.dialog.add("imagebutton", function(d) {
        return v(d, "imagebutton")
    })
})();