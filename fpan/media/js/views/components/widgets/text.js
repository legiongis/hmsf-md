define(['knockout', 'underscore', 'viewmodels/widget'], function (ko, _, WidgetViewModel) {
    /**
    * registers a text-widget component for use in forms
    * @function external:"ko.components".text-widget
    * @param {object} params
    * @param {string} params.value - the value being managed
    * @param {function} params.config - observable containing config object
    * @param {string} params.config().label - label to use alongside the text input
    * @param {string} params.config().placeholder - default text to show in the text input
    */
    return ko.components.register('text-widget', {        
        viewModel: function(params) {
            params.configKeys = ['placeholder', 'width', 'maxLength', 'defaultValue'];
            var self = this;
            if (params.state != 'report' && params.tile.tileid == "" ) {
                //set a default value for an observable
                ko.extenders.defaultIfNull = function(target, defaultVal) {
                    var result = ko.computed({
                        read: target,
                        write: function(newVal) {
                            if (!newVal) {
                                target(defaultVal);
                                if (params.node.id == 'a72bbb27-bd5d-11e9-9b8f-94659cf754d0') {
                                    params.value(defaultVal);
                                }
                            } else {
                                target(newVal);                                 
                                if (params.node.id == 'a72bbb27-bd5d-11e9-9b8f-94659cf754d0') {
                                    params.value(newVal);
                                }
                            }
                        }
                    });
                    result(target());
                    return result;
                }
                self.username = ko.observable().extend({ defaultIfNull: params.user });
                self.username.subscribe(function(newValue) {
                    params.value(newValue);
                });
                self.username.subscribe(function(oldValue) {
                    params.value(oldValue);
                }, null, "beforeChange");         
            }
            WidgetViewModel.apply(this, [params]);     
        },
        template: { require: 'text!widget-templates/text' }
    });
});
