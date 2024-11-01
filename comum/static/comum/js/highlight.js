highlight_behave = function(element) {
    function px(value) {
        return value + "px";
    }

    var window_height = ($(window).height() > $(document).height() ? $(window).height() : $(document).height());
    var window_width = ($(window).width() > $(document).width() ? $(window).width() : $(document).width());
    for (var index = 0; index < 12; index++) {
        var offset = element.offset();
        var top = 0, left = 0, width = element.outerWidth(), height = window_height;
        var border = "";
        var background_color = "rgba(0,0,0,0.2)";
        var z_index = 10;
        switch (index) {
            case 0:
                top = 0;
                width = offset.left;
                left = 0;
                height = offset.top;
                break;
            case 1:
                top = 0;
                width = element.outerWidth();
                left = offset.left;
                height = offset.top;
                border = "bottom";
                break;
            case 2:
                top = element.outerHeight() + offset.top;
                left = offset.left;
                height = height - top;
                border = "top";
                break;
            case 3:
                top = 0;
                height = offset.top;
                left = element.outerWidth() + offset.left;
                width = window_width - left;
                break;
            case 4:
                top = offset.top;
                left = element.outerWidth() + offset.left;
                width = window_width - left;
                height = element.outerHeight();
                border = "left";
                break;
            case 5:
                top = element.outerHeight() + offset.top;
                left = element.outerWidth() + offset.left;
                width = window_width - left;
                height = window_height - top;
                break;
            case 6:
                top = element.outerHeight() + offset.top;
                left = 0;
                width = offset.left;
                height = window_height - top;
                break;
            case 7:
                top = offset.top;
                left = 0;
                width = offset.left;
                height = element.outerHeight();
                border = "right";
                break;
            case 8:
                top = offset.top - 5;
                left = offset.left - 5;
                width = 5;
                height = 5;
                background_color = "red";
                z_index = 11;
                break;
            case 9:
                top = offset.top - 5;
                left = element.outerWidth() + offset.left;
                width = 5;
                height = 5;
                background_color = "red";
                z_index = 11;
                break;
            case 10:
                top = element.outerHeight() + offset.top;
                left = element.outerWidth() + offset.left;
                width = 5;
                height = 5;
                background_color = "red";
                z_index = 11;
                break;
            case 11:
                top = element.outerHeight() + offset.top;
                left = offset.left - 5;
                width = 5;
                height = 5;
                background_color = "red";
                z_index = 11;
                break;

        }
        var styles = "top:" + px(top) + ";left:" + px(left) + ";width:" + px(width) + ";height:" + px(height) + ";border-"+ border +": 5px solid red" + ";background-color: "+ background_color+ "; z-index: "+ z_index +"; position: absolute;";
        $("body").prepend("<div class='highlight_behave index"+ index+ "' style='" + styles + "'></div>");
    }
};
