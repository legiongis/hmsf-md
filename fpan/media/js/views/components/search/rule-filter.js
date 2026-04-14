define([
    'knockout',
    'views/components/search/base-filter',
    'templates/views/components/search/rule-filter.htm'
], function(ko, BaseFilter, ruleFilterTemplate) {
    var componentName = 'rule-filter';
    return ko.components.register(componentName, {
        viewModel: BaseFilter.extend({
            initialize: function(options) {
                options.name = 'Rule Filter';
                BaseFilter.prototype.initialize.call(this, options);
                this.restoreState();
            },

            restoreState: function() {
                var queryObj = this.query();
                queryObj[componentName] = 'enabled';
                this.query(queryObj);
            },

        }),
        template: ruleFilterTemplate
    });
});
