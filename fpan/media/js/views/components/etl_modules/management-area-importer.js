/* eslint-disable @typescript-eslint/no-this-alias */
define([
    'underscore',
    'knockout',
    'viewmodels/base-import-view-model',
    'uuid',
    'arches',
    'viewmodels/alert',
    'templates/views/components/etl_modules/management-area-importer.htm',
    'dropzone',
    'bindings/select2-query',
    'bindings/dropzone',
], function(_, ko, ImporterViewModel, uuid, arches, AlertViewModel, managementAreaImporterTemplate) {
    return ko.components.register('management-area-importer', {
        viewModel: function(params) {
            const self = this;
            this.loadId = params.loadId || uuid.generate();
            this.loadDetails = params.load_details || ko.observable();
            this.state = params.state;
            this.loading = params.loading || ko.observable();
            this.data2 = ko.observable(false);

            const blankOption = {"name": "---", "id": "---"};
            this.maGroup = ko.observable("");
            this.maGroupOptions = ko.observableArray([blankOption]);
            this.maCategory = ko.observable("");
            this.maCategoryOptions = ko.observableArray([blankOption]);
            this.maAgency = ko.observable("");
            this.maAgencyOptions = ko.observableArray([blankOption]);
            this.maLevel = ko.observable("");
            this.maLevelOptions = ko.observableArray([blankOption]);

            this.loadDescription = ko.observable("");

            this.moduleId = params.etlmoduleid;
            ImporterViewModel.apply(this, arguments);
            this.templates = ko.observableArray();
            this.selectedTemplate = ko.observable();
            this.loadStatus = ko.observable('ready');

            this.validated = ko.observable();
            this.validationError = ko.observableArray();
            this.selectedLoadEvent = params.selectedLoadEvent || ko.observable();

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
                    self.loadId = data.result.loadid;
                } else {
                    console.log('error');
                    self.loading(false);
                }
            };



            fetch("/select-lists/management-area-data")
                .then(response => response.json())
                .then(data => {
                    console.log(data);
                    data.ma_agency_opts.forEach(i => self.maAgencyOptions.push(i));
                    data.ma_category_opts.forEach(i => self.maCategoryOptions.push(i));
                    data.ma_group_opts.forEach(i => self.maGroupOptions.push(i));
                    data.ma_level_opts.forEach(i => self.maLevelOptions.push(i));
                });

            this.start = async function(){
                self.loading(true);
                self.formData.append("maGroup", self.maGroup().id);
                self.formData.append("maCategory", self.maCategory().id);
                self.formData.append("maAgency", self.maAgency().id);
                self.formData.append("maLevel", self.maLevel().id);
                self.formData.append("loadDescription", self.loadDescription());
                self.formData.append("loadId", self.loadId);
                const response = await self.submit('run_web_import');
                self.loading(false);
                params.activeTab("import");
                if (response.ok) {
                    const data = await response.json();
                    self.response(data);
                } else {
                    console.log('error');
                    self.loading(false);
                }
            };
        },
        template: managementAreaImporterTemplate
    });
});
