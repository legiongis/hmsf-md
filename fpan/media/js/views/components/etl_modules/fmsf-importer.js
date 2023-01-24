define([
    'underscore',
    'knockout',
    'viewmodels/base-import-view-model',
    'uuid',
    'arches',
    'viewmodels/alert',
    'dropzone',
    'bindings/select2-query',
    'bindings/dropzone',
], function(_, ko, ImporterViewModel, uuid, arches, AlertViewModel) {
    return ko.components.register('fmsf-importer', {
        viewModel: function(params) {
            const self = this;
            this.loadId = params.loadId || uuid.generate();
            this.loadDetails = params.load_details || ko.observable();
            this.state = params.state;
            this.loading = params.loading || ko.observable();
            this.data2 = ko.observable(false);

            this.resourceType = ko.observable("");
            this.truncate = ko.observable(0);
            this.dryRun = ko.observable(false);
            this.loadDescription = ko.observable("");

            this.moduleId = params.etlmoduleid;
            ImporterViewModel.apply(this, arguments);
            this.templates = ko.observableArray();
            this.selectedTemplate = ko.observable();
            this.loadStatus = ko.observable('ready');

            this.addFile = async function(file){
                self.loading(true);
                self.fileInfo({name: file.name, size: file.size});
                const formData = new window.FormData();
                formData.append('file', file, file.name);
                const response = await self.submit('read_zip', formData);
                if (response.ok) {
                    const data = await response.json();
                    self.loading(false);
                    self.response(data);
                    self.loadDetails(data);
                } else {
                    // eslint-disable-next-line no-console
                    console.log('error');
                    self.loading(false);
                }
            };

            this.start = async function(){
                self.loading(true);
                self.formData.append("resourceType", self.resourceType())
                self.formData.append("truncate", self.truncate())
                self.formData.append("dryRun", self.dryRun())
                self.formData.append("loadDescription", self.loadDescription())
                const response = await self.submit('run_web_import');
                self.loading(false);
                params.activeTab("import");
                if (response.ok) {
                    const data = await response.json();
                    self.response(data);
                } else {
                    // eslint-disable-next-line no-console
                    console.log('error');
                    self.loading(false);
                }
            };
        },
        template: { require: 'text!templates/views/components/etl_modules/fmsf-importer.htm' }
    });
});
