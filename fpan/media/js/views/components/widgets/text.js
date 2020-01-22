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
            
            ko.extenders.defaultIfNull = function(target, defaultVal) {
                var result = ko.computed({
                    read: target,
                    write: function(newVal) {
                        if (!newVal) {
                            target(defaultVal);
                        } else {
                            target(newVal);
                        }
                    }
                });
                result(target());
                return result;
            };
            this.username = ko.observable().extend({ defaultIfNull: params.user });
       
           var subscription1 = this.username.subscribe(function(newValue) {
                params.value(newValue);
            });
            var subscription2 = this.username.subscribe(function(oldValue) {
                params.value(oldValue);
            }, null, "beforeChange");
            
            subscription1.dispose();
            subscription2.dispose();

            WidgetViewModel.apply(this, [params]);     
        },
        template: { require: 'text!widget-templates/text' }
    });
});
