define(['knockout',
        'knockout-mapping',
        'views/list',
        'viewmodels/function',
        'bindings/chosen'],
function (ko, koMapping, ListView, FunctionViewModel, chosen) {
    return ko.components.register('views/components/functions/sample-function', {
        viewModel: function(params) {
            FunctionViewModel.apply(this, arguments);
            console.log("Running a sample function")
            var self = this;
            var nodegroups = {};
            this.cards = ko.observableArray();
            this.selected_nodegroup = params.config.selected_nodegroup;
            this.triggering_nodegroups = params.config.triggering_nodegroups;
            this.selected_nodegroup.subscribe(function(ng){
              console.log('this is run because a new value is set for the selected_nodgroup variable', ng);
              self.config.triggering_nodegroups = [ng];
            })
            
            self.config.newvar = "adinfeinf"

            // this.graph.cards.forEach(function(card){
                // var found = !!_.find(this.graph.nodegroups, function(nodegroup){
                    // return nodegroup.parentnodegroup_id === card.nodegroup_id
                // }, this);
                // if(!found && !(card.nodegroup_id in nodegroups)){
                    // this.cards.push(card);
                    // nodegroups[card.nodegroup_id] = true;
                // }
            // }, this);
            
            this.graph.nodes.forEach(function(node){
                console.log(node);
                this.cards.push(node);
            }, this);
            
            
            console.log(params);

            window.setTimeout(function(){$("select[data-bind^=chosen]").trigger("chosen:updated")}, 300);
        },
        template: {
            require: 'text!templates/views/components/functions/sample-function.htm'
        }
    });
})
