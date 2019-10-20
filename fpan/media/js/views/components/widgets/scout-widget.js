define(['knockout', 'underscore', 'viewmodels/widget', 'jquery', 'fpan','bindings/chosen'], function (ko, _, WidgetViewModel, $, fpan, chosen) {
    /**
    * registers a text-widget component for use in forms
    * @function external:"ko.components".text-widget
    * @param {object} params
    * @param {string} params.value - the value being managed
    * @param {function} params.config - observable containing config object
    * @param {string} params.config().label - label to use alongside the text input
    * @param {string} params.config().placeholder - default text to show in the text input
    */
    return ko.components.register('scout-widget', {
        viewModel: function(params) {
            params.configKeys = ['options','placeholder'];
            WidgetViewModel.apply(this, [params]);

            var self = this;
            self.availableScouts = ko.observableArray();
            self.selectedScout = params.value;
            
            if (params.state != 'report') {
                $.ajax({
                    url: fpan.urls.scouts_dropdown,
                    data: {
                        'resourceid': self.resourceid
                    },
                    dataType: "json"
                }).done(function(data) {
                    $.each(data, function() {
                        self.availableScouts.push(this);
                    });
                    // refresh the observable array, necessary because of async ajax
                    self.availableScouts.valueHasMutated();
                });
            }
        },
        template: { require: 'text!templates/views/components/widgets/scout-widget.htm' }
    });
});
