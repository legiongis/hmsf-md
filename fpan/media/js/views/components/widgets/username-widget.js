define([
    'knockout',
    'viewmodels/domain-widget',
    'widget-data',
    'plugins/knockout-select2'
], function(ko, DomainWidgetViewModel, widgetData) {
    /**
     * registers a select-widget component for use in forms
     * @function external:"ko.components".select-widget
     * @param {object} params
     * @param {boolean} params.value - the value being managed
     * @param {object} params.config -
     * @param {string} params.config.label - label to use alongside the select input
     * @param {string} params.config.placeholder - default text to show in the select input
     * @param {string} params.config.options -
     */
    return ko.components.register('username-widget', {
        viewModel: function(params) {
            params.configKeys = ['placeholder', 'defaultValue'];

            if (!params.node.config) {
              params.node.config = {};
            }
            if (!params.node.configKeys) {
              params.node.configKeys = {};
            }
            params.node.config.options = ko.observableArray(widgetData.dropdownLists.usernames)

            DomainWidgetViewModel.apply(this, [params]);

            var self = this;
            if (self.value() == null || self.value().length == 0) {
              widgetData.dropdownLists.usernames.forEach( function (user) {
                if (user.text == params.user) {
                  self.value([user.id])
                }
              })
            }

            this.multiple = true;
        },
        template: {
            require: 'text!widget-templates/select'
        }
    });
});
