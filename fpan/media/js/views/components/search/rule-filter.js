define([
    'knockout',
    'arches',
    'views/components/search/base-filter',
    'templates/views/components/search/rule-filter.htm'
], function(ko, arches, BaseFilter, ruleFilterTemplate) {
    var componentName = 'rule-filter';
    const viewModel = BaseFilter.extend({
        initialize: async function(options) {

            options.name = 'Rule Filter';
            BaseFilter.prototype.initialize.call(this, options);

            const response = await fetch(arches.urls.api_search_component_data + componentName);
                if (response.ok) {
                    const data = await response.json();
                    this.rule_filter_html(data.rule_filter_html);
                } else {
                    this.rule_filter_html('Failed to fetch rule-filter summary');
                }

            this.searchFilterVms[componentName](this);
            this.restoreState();
        },

        rule_filter_html: ko.observable(),

        restoreState: function() {
            var query = this.query();
            query[componentName] = "enabled";
            this.query(query);
        }

    });
    return ko.components.register(componentName, {
        viewModel: viewModel,
        template: ruleFilterTemplate,
    });
});
