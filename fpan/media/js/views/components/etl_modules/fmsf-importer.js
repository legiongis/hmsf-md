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

            this.moduleId = params.etlmoduleid;
            ImporterViewModel.apply(this, arguments);
            this.templates = ko.observableArray();
            this.selectedTemplate = ko.observable();
            this.loadStatus = ko.observable('ready');

            // this.downloadTemplate = async () => {
            //     const url = `/etl-manager`;
            //     const formData = new window.FormData();
            //     formData.append("id", ko.unwrap(this.selectedTemplate));
            //     formData.append("format", "xls");
            //     formData.append("module", ko.unwrap(self.moduleId));;
            //     formData.append("action", "download");
                
            //     const response = await window.fetch(url, {
            //         method: 'POST',
            //         body: formData,
            //         credentials: 'same-origin',
            //         headers: {
            //             "Accept": "application/json",
            //             "X-CSRFToken": getCookie("csrftoken")
            //         }
            //     });

            //     const blob = await response.blob();
            //     const urlObject = window.URL.createObjectURL(blob);
            //     const a = window.document.createElement('a');
            //     window.document.body.appendChild(a);
            //     a.href = urlObject;
            //     a.download = `${this.templates().filter(x => x.id == this.selectedTemplate())[0].text}.xlsx`;
            //     a.click();

            //     setTimeout(() => {
            //         window.URL.revokeObjectURL(urlObject);
            //         window.document.body.removeChild(a);
            //     }, 0);
            //     this.loading(false);
            // };

            this.addFile = async function(file){
                self.loading(true);
                self.fileInfo({name: file.name, size: file.size});
                const formData = new window.FormData();
                formData.append('file', file, file.name);
                const response = await self.submit('read_zip', formData);
                console.log(response)
                if (response.ok) {
                    const data = await response.json();
                    console.log(data);
                    // self.loadId = data.loadid;
                    self.loading(false);
                    console.log(1);
                    self.response(data);
                    console.log(2);
                    self.loadDetails(data);
                } else {
                    // eslint-disable-next-line no-console
                    console.log('error');
                    self.loading(false);
                }
            };

            this.start = async function(){
                self.loading(true);
                const response = await self.submit('run_web_import');
                self.loading(false);
                params.activeTab("import");
                if (response.ok) {
                    const data = await response.json();
                    self.response(data); 
                    console.log(data)
                    // self.write();
                }
            };

            // this.write = async function(){
            //     self.loading(true);
            //     const formData = new window.FormData();
            //     formData.append('load_details', JSON.stringify(self.loadDetails()));
            //     console.log("in write")
            //     console.log(formData)
            //     const response = await self.submit('write', formData);
            //     self.loading(false);
            //     if (response.ok) {
            //         const data = await response.json();
            //         self.response(data); 
            //     }
            //     else {
            //         const data = await response.json();
            //         this.alert(new AlertViewModel(
            //             'ep-alert-red',
            //             data["data"]["title"],
            //             data["data"]["message"],
            //             null,
            //             function(){}
            //         ));
            //     }
            // };
        },
        template: { require: 'text!templates/views/components/etl_modules/fmsf-importer.htm' }
    });
});
