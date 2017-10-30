define(['knockout',
        'knockout-mapping',
        'views/list',
        'viewmodels/function',
        'bindings/chosen'],
function (ko, koMapping, ListView, FunctionViewModel, chosen) {
    return ko.components.register('views/components/functions/spatial-join', {
        viewModel: function(params) {
            FunctionViewModel.apply(this, arguments);
            var self = this;
            
            // create a ko observable that can be used by the select2 widgets
            // note that the widget needs to be configured to record the correct
            // property (nodeid, nodegroup_id, etc.)
            this.nodes = ko.observableArray();
            this.graph.nodes.forEach(function(node){
                this.nodes.push(node);
            }, this);
            
            // set triggering nodegroup variable so it can be updated below
            // to run a function, you must provide at least one nodegroup_id
            // to this variable. note that it must be a nodegroup_id, not just
            // a nodeid.
            this.triggering_nodegroups = params.config.triggering_nodegroups;

            // set spatial node id from existing params
            this.spatial_node_id = params.config.spatial_node_id;
            
            // and subscribe it so it updates automatically as the select2
            // widget is used. note that the widget must reference this variable
            // name. the function may be empty, but in this case we need to use
            // it to get the nodegroup_id of the selected node and then update
            // the triggering_nodegroup config variable. 
            this.spatial_node_id.subscribe(function(ng){
                
                // 
                var node_array = self.nodes()
                node_array.forEach(function(node){
                  if (ng == node.nodeid) {
                      self.config.triggering_nodegroups = [node.nodegroup_id];
                  }
              });
            })

            // the following three sections are simpler versions of above; set
            // a variable based on previous config value, and subscribe it to
            // the input widget that references this variable name
            this.table_field_one = params.config.table_field_one;
            this.table_field_one.subscribe(function(ng){});
            
            this.target_node_id_one = params.config.target_node_id_one;
            this.target_node_id_one.subscribe(function(ng){});
            
            this.table_field_two = params.config.table_field_two;
            this.table_field_two.subscribe(function(ng){});
            
            this.target_node_id_two = params.config.target_node_id_two;
            this.target_node_id_two.subscribe(function(ng){});

            window.setTimeout(function(){$("select[data-bind^=chosen]").trigger("chosen:updated")}, 300);
        },
        template: {
            require: 'text!templates/views/components/functions/spatial-join.htm'
        }
    });
})
