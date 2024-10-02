(function($) {
    $(document).on('formset:added', function(event, $row, formsetName) {
    	var contador = $('input[id="id_'+formsetName+'-TOTAL_FORMS"]')[0].value - 1;
		var newFormHtml = $row.html().replace(new RegExp('__prefix__', 'g'), contador).replace(new RegExp('<\\\\/script>', 'g'), '</script>');
		$row.html(newFormHtml);
		$row.find('.related-widget-wrapper').each(function(windex, wobj) {
			$(wobj).children('span').last().remove();
		});
    });

    $(document).on('formset:removed', function(event, $row, formsetName) {
    	
    });
})(django.jQuery);