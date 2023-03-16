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
    return ko.components.register('management-area-importer', {
        viewModel: function(params) {
            const self = this;
            this.loadId = params.loadId || uuid.generate();
            this.loadDetails = params.load_details || ko.observable();
            this.state = params.state;
            this.loading = params.loading || ko.observable();
            this.data2 = ko.observable(false);

            this.maGroup = ko.observable("");
            this.maCategory = ko.observable("");
            this.maAgency = ko.observable("");
            this.maLevel = ko.observable("");
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
                console.log(self.loadId)
                if (response.ok) {
                    const data = await response.json();
                    self.loading(false);
                    self.response(data);
                    self.loadDetails(data);
                    self.loadId = data.result.loadid;
                } else {
                    // eslint-disable-next-line no-console
                    console.log('error');
                    self.loading(false);
                }
            };

            this.start = async function(){
                self.loading(true);
                self.formData.append("maGroup", self.maGroup())
                self.formData.append("maCategory", self.maCategory())
                self.formData.append("maAgency", self.maAgency())
                self.formData.append("maLevel", self.maLevel())
                self.formData.append("loadDescription", self.loadDescription())
                self.formData.append("loadId", self.loadId)
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
        template: { require: 'text!templates/views/components/etl_modules/management-area-importer.htm' }
    });
});
