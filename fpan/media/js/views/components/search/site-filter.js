define([
    'knockout',
    'views/components/search/base-filter',
    'fpan'
], function(ko, BaseFilter, FPAN) {
    var componentName = 'site-filter';
    console.log("at the top of the file");
    return ko.components.register(componentName, {
        viewModel: BaseFilter.extend({
            initialize: function(options) {
                options.name = 'Site Filter';

                console.log("initializing site filter");
                BaseFilter.prototype.initialize.call(this, options);

                this.restoreState();
            },

            // this doesn't seem to be used anywhere and can likely be removed.
            updateQuery: function() {
                console.log("updating query");
                var queryObj = this.query();
                queryObj[componentName] = 'enabled';
                this.query(queryObj);
            },

            restoreState: function() {
                console.log("restoring state");
                var queryObj = this.query();
                if (FPAN.full_site_access == "True") {
                  queryObj[componentName] = 'disabled';
                } else {
                  queryObj[componentName] = 'enabled';
                }
                this.query(queryObj);
            },

        }),
        template: { require: 'text!templates/views/components/search/site-filter.htm' }
    });
});
