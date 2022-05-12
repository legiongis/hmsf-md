define([
    'knockout',
    'views/components/search/base-filter',
], function(ko, BaseFilter) {
    var componentName = 'scout-report-filter';
    return ko.components.register(componentName, {
        viewModel: BaseFilter.extend({
            initialize: function(options) {
                options.name = 'Scout Report Filter';
                BaseFilter.prototype.initialize.call(this, options);
            },

            enabled: ko.observable(false),

            updateQuery: function() {
                this.enabled(!this.enabled())                
                var queryObj = this.query();
                if(this.enabled()){
                    queryObj[componentName] = 'enabled';
                } else {
                    delete queryObj[componentName];
                }
                this.query(queryObj);
            },

        }),
        template: { require: 'text!templates/views/components/search/scout-report-filter.htm' }
    });
});
