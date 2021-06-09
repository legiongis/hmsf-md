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
    return ko.components.register('management-area-widget', {
        viewModel: function(params) {
            params.configKeys = ['options','placeholder'];
            WidgetViewModel.apply(this, [params]);

            var self = this;
            self.available = ko.observableArray();
            self.selected = params.value;
            self.multiple = true;
            $.ajax({
                url: fpan.urls.management_areas_dropdown,
                dataType: "json"
            }).done(function(data) {
                $.each(data, function() {
                    self.available.push(this);
                });
                // refresh the observable array, necessary because of async ajax
                self.available.valueHasMutated();
            });
        },
        template: { require: 'text!templates/views/components/widgets/management-area-widget.htm' }
    });
});
