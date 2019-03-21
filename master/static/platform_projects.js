function initData(dataList, pageSize, pageNum) {
    let tBody = $("#tBody");
    let tbHtml = '';
    //遍历数据添加
    $.each(dataList, function (key, project) {
        tbHtml += '<tr>';
        tbHtml += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        tbHtml += '<td><a href="./detail/' + project.vc_md5 + '">' + project.project_name + '</a></td>';
        tbHtml += '<td>' + project.version_name + '</td>';
        tbHtml += '<td>' + project.versions.length + '</td>';
        tbHtml += '<td>' + project.spiders.length + '</td>';
        tbHtml += '<td><a type="button" class="btn btn-danger" href="/project/delete/' + project.project_name + '">Delete</a></td>';
        tbHtml += '</tr>';
    });
    // 装载数据 加载事件
    tBody.empty().append(tbHtml).find('.btn-danger').click(function () {
        let msg = "确定要删除吗？\n\n请确认！";
        return confirm(msg);
    });
    return tbHtml;
}

function pageSearch(event, pageNum) {
    let ajaxUrl = "/project/search";
    let searchString = $("#searchString").val();  // 得到查询条件
    let pageSize = $("#pageSize").val();  // 得到每页显示条数
    if (!pageNum) {
        pageNum = 1;  // 得到显示第几页
    }
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"pageNum": pageNum, "pageSize": pageSize, "keywords": searchString},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (pagination) {
                if (!pagination) {
                    return  // 失败，请重试
                }
                let dataList = pagination.items;
                let pager = $("#pager");
                pager.empty();
                pager.append(initPage(pagination));
                pager.find('li a').click(function () {
                    pageSearch(null, $(this).attr("data-id"))
                });
                initData(dataList, pageSize, pageNum)
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function pageSearchDetail(event) {
    let ajaxUrl = "/project/detail/search";
    let searchString = $("#searchString").val();  // 得到查询条件
    let tBody = $("#tBody");
    let dataID = tBody.attr("data-id");
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"keywords": searchString, "dataID": dataID},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (dataList) {
                let tbHtml = '';
                //遍历数据添加
                $.each(dataList, function (key, project) {
                    tbHtml += '<tr>';
                    tbHtml += '<td>' + (key + 1) + '</td>';
                    tbHtml += '<td>' + project.project_name + '</td>';
                    tbHtml += '<td>' + project.version_name + '</td>';
                    let spidersLength = project.spiders.length;
                    if (spidersLength <= 0) {
                        tbHtml += '<td>0</td>';
                        tbHtml += '<td><a type="button" class="btn btn-danger" href="/project/delete/' + project.project_name + '/' + project.version_name + '">Delete</a></td>';
                        tbHtml += '</tr>';
                    }
                    else {
                        tbHtml += '<td><a data-toggle="collapse" data-parent="#tBody" href="#collapse_' + project.vc_md5 + '">' + spidersLength + '</a></td>';
                        tbHtml += '<td><a type="button" class="btn btn-danger" href="/project/delete/' + project.project_name + '/' + project.version_name + '">Delete</a></td>';
                        tbHtml += '</tr>';

                        tbHtml += '<tr id="collapse_' + project.vc_md5 + '" class="panel-collapse collapse">';
                        tbHtml += '<td colspan="5">';
                        tbHtml += '<table class="table"><thead><tr>';
                        tbHtml += '<th style="width: 30px">Index</th>';
                        tbHtml += '<th style="width: 80px">SpiderName</th>';
                        tbHtml += '<th style="width: 120px">StartTime(Last)</th>';
                        tbHtml += '<th style="width: 80px">WaitingTime(Avg)</th>';
                        tbHtml += '<th style="width: 80px">RunningTime(Avg)</th>';
                        tbHtml += '<th style="width: 50px">RunsNum</th>';
                        tbHtml += '<th style="width: 80px">Operation</th>';
                        tbHtml += '</tr></thead><tbody>';
                        $.each(project.spiders, function (i, spider) {
                            tbHtml += '<tr>';
                            tbHtml += '<td>' + (i + 1) + '</td>';
                            tbHtml += '<td>' + spider.spider_name + '</td>';
                            tbHtml += '<td>' + spider.start_time_last + '</td>';
                            tbHtml += '<td>' + spider.waiting_time_avg + '</td>';
                            tbHtml += '<td>' + spider.running_time_avg + '</td>';
                            tbHtml += '<td>' + spider.runs_num + '</td>';
                            tbHtml += '<td><a type="button" class="btn btn-info" href="/project/start/' + project.project_name + '/' + spider.spider_name + '/' + project.version_name + '">Start</a></td>';
                            tbHtml += '</tr>';
                        });
                        tbHtml += '</tbody></table>';
                        tbHtml += '</td></tr>';
                    }
                });
                // 装载数据 加载事件
                tBody.empty().append(tbHtml).find('.btn-danger').click(function () {
                    let msg = "确定要删除吗？\n\n请确认！";
                    return confirm(msg);
                });
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}