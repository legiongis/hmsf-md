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
    return ko.components.register('username-widget', {
        viewModel: function(params) {
            params.configKeys = ['options', 'placeholder', 'defaultValue'];
            WidgetViewModel.apply(this, [params]);

            var self = this;
            self.availableOptions = ko.observableArray();
            self.selectedOption = params.value;
            self.multiple = true;

            async function updateDropdownList() {
              await new Promise(r => setTimeout(r, 500));
              fpan.user_list.forEach( function (user) {
                self.availableOptions.push(user)
              });
              self.availableOptions.valueHasMutated();
            }
            updateDropdownList();

            if (params.widget && this.value() == "{current-user}") {
              this.value(params.user);
            }
        },
        template: { require: 'text!templates/views/components/widgets/username-widget.htm' }
    });
});
