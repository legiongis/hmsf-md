define([
    'knockout',
    'views/components/search/base-filter'
], function(ko, BaseFilter) {
    var componentName = 'site-filter';
    return ko.components.register(componentName, {
        viewModel: BaseFilter.extend({
            initialize: function(options) {
                options.name = 'Site Filter';
                BaseFilter.prototype.initialize.call(this, options);

                this.filter = ko.observableArray();

                // this is where the filter gets added to the list of available filters
                this.filters[componentName](this);

                // this is so if you refresh the page the url parameter is restored
                this.restoreState();
            },

            updateQuery: function() {
                var queryObj = this.query();
                this.query(queryObj);
            },

            restoreState: function() {
                var query = this.query();
            },

            clear: function() {
                this.filter.removeAll();
            }

        }),
        template: { require: 'text!templates/views/components/search/site-filter.htm' }
    });
});
