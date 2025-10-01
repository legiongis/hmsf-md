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

            self.downloadPhotos = function (baseUrl) {
                var url = baseUrl + self.report.get('resourceid');
                var response;
                fetch(url)
                    .then(function (resp) {
                        /*
                        not handling bad status codes because...
                        - if no photos associated with report, user doesn't see
                        Save Images button, so they can't make the request anyway
                        - this resource and its id must exist because we click
                        Save Images from the report view, so the server will always
                        get this request with a qualifying report (resource) id
                        */
                        response = resp;
                        return resp.blob();
                    })
                    .then(function (blob) {
                        var filename = response.headers.get('Content-Disposition')
                            .match(/filename="(.+)"/)[1]
                            || 'report-photos.zip'

                        // download by clicking a temp link
                        var a = document.createElement('a');
                        a.download = filename;
                        a.href = URL.createObjectURL(blob);;
                        a.click();
                        a.remove();
                        URL.revokeObjectURL(blob);
                    })
                    .catch(function(err) {
                        console.error(err)
                        alert("Couldn't reach the server. Please try again later.")
                    });
            }
        },
        template: {
            require: 'text!report-templates/image'
        }
    });
});
