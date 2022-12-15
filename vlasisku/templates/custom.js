function search() {
    window.location = "{{ url_for('app.query', query='') }}" + encodeURIComponent(jQuery('#query').attr('value'));
    return false;
}

jQuery(function ($) {
    $('a').tipTip({maxWidth: '600px'});
    $('#query').autocomplete("{{ url_for('app.complete') }}", {
        delay: 0,
        matchCase: true,
        selectFirst: false
    });
    $(window).load(function () {
        $('#query').attr('autocomplete', 'off');
    });
});
