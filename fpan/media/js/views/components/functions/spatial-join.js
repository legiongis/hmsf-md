define(['knockout',
        'knockout-mapping',
        'views/list',
        'viewmodels/function',
        'bindings/chosen'],
function (ko, koMapping, ListView, FunctionViewModel, chosen) {
    return ko.components.register('views/components/functions/spatial-join', {
        viewModel: function(params) {
            FunctionViewModel.apply(this, arguments);
            console.log("Running...")
            var self = this;
            // var nodegroups = {};
            this.nodes = ko.observableArray();
            
            
            this.spatial_node_id = params.config.spatial_node_id;
            this.triggering_nodegroups = params.config.triggering_nodegroups;
            this.spatial_node_id.subscribe(function(ng){
              console.log('this is run because a new value is set for the spatial_node_id variable', ng);
              self.config.triggering_nodegroups = [ng];
            })

            this.table_name = params.config.table_name;
            this.table_name.subscribe(function(ng){});
            
            this.field_name = params.config.field_name;
            this.field_name.subscribe(function(ng){});
            
            this.target_node_id = params.config.target_node_id;
            this.target_node_id.subscribe(function(ng){});
            
            this.graph.nodes.forEach(function(node){
                console.log(node);
                this.nodes.push(node);
            }, this);
            
            
            console.log(params);

            window.setTimeout(function(){$("select[data-bind^=chosen]").trigger("chosen:updated")}, 300);
        },
        template: {
            require: 'text!templates/views/components/functions/spatial-join.htm'
        }
    });
})
