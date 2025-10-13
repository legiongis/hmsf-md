define([
    'underscore',
    'knockout',
    'knockout-mapping',
    'viewmodels/report',
    'arches',
    'knockstrap',
    'bindings/chosen'
], function(_, ko, koMapping, ReportViewModel, arches) {
    return ko.components.register('image-report', {
        viewModel: function(params) {
            var self = this;
            params.configKeys = ['nodes'];
            ReportViewModel.apply(this, [params]);

            self.hasImages = true; // used to show/hide Save Images button

            self.imgs = ko.computed(function() {
                var imgs = [];
                var nodes = ko.unwrap(self.nodes);
                self.tiles().forEach(function(tile) {
                    _.each(tile.data, function(val, key) {
                        val = koMapping.toJS(val);
                        if (Array.isArray(val)) {
                            val.forEach(function(item) {
                                if (item.status &&
                                    item.type &&
                                    item.status === 'uploaded' &&
                                    item.type.indexOf('image') > -1 &&
                                    _.contains(nodes, key)
                                ) {
                                    imgs.push({
                                        // with s3 urls, the replace() messed things up (FPAN fix)
                                        //src: (arches.urls.url_subpath + ko.unwrap(item.url)).replace('//', '/'),
                                        src: (arches.urls.url_subpath + ko.unwrap(item.url)),
                                        alt: item.name
                                    });
                                }
                            });
                        }
                    }, self);
                }, self);
                if (imgs.length === 0) {
                    self.hasImages = false;
                    imgs = [{
                        src: arches.urls.media + 'img/photo_missing.png',
                        alt: ''
                    }];
                }
                return imgs;
            });

            var widgets = [];
            var getCardWidgets = function(card) {
                widgets = widgets.concat(card.model.get('widgets')());
                card.cards().forEach(function(card) {
                    getCardWidgets(card);
                });
            };
            ko.unwrap(self.report.cards).forEach(getCardWidgets);
            this.nodeOptions = ko.observableArray(
                widgets.map(function(widget) {
                    return widget.node;
                }).filter(function(node) {
                    return ko.unwrap(node.datatype) === 'file-list';
                })
            );

            /*
            `isDownloadingPhotos` binds to a spinner in the Download Photos
            button. The user needs immediate feedback that the server has
            started the job because:
                - the browser won't show feedback about the download until the
                    server responds
                - the initial response will take a while to arrive (fetching
                    from S3 and zipping photos)
            */
            self.isDownloadingPhotos = ko.observable(false)

            self.downloadPhotos = function (baseUrl) {
                self.isDownloadingPhotos(true);
                var resourceid = self.report.get('resourceid');
                var url = baseUrl + resourceid;
                var response;
                fetch(url)
                    .then(function (resp) {
                        if (!resp.ok) {
                            err = new Error();
                            err.isServerErr = true;
                            throw err;
                        }
                        response = resp;
                        return resp.blob();
                    })
                    .then(function (blob) {
                        var filename = response.headers.get('Content-Disposition')
                            .match(/filename="(.+)"/)[1]
                            || `report-photos-${resourceid}.zip`;
                        var a = document.createElement('a');
                        a.download = filename;
                        a.href = URL.createObjectURL(blob);
                        a.click();
                        a.remove();
                        URL.revokeObjectURL(a.href);
                    })
                    .catch(function(err) {
                        // need this check to silence the error alert when the
                        // user leaves the page during the downlaod
                        if (!err.isServerErr) return;
                        var msg = "There was an issue on the server.\nPlease try downloading again later.";
                        console.error(msg + ': ' +  err);
                        alert(msg);
                    })
                    .finally(function() { self.isDownloadingPhotos(false); });
            }
        },
        template: {
            require: 'text!report-templates/image'
        }
    });
});
