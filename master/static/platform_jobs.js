function initData(dataList, pageSize, pageNum) {
    let jobStatus = $("#dataType").val();

    let tHead = $("#tHead");
    let thHtml = '';
    thHtml += '<tr>';
    thHtml += '<th style="width: 30px">Index</th>';
    thHtml += '<th style="width: 80px">JobID</th>';
    thHtml += '<th style="width: 80px">Slave</th>';
    thHtml += '<th style="width: 80px">Project</th>';
    thHtml += '<th style="width: 80px">Spider</th>';
    thHtml += '<th style="width: 80px">Plan</th>';
    if (jobStatus === 'pending') {
        thHtml += '<th style="width: 80px">CreateTime</th>';
        thHtml += '<th style="width: 80px">WaitingTime</th>';
    } else if (jobStatus === 'running') {
        thHtml += '<th style="width: 80px">StartTime</th>';
        thHtml += '<th style="width: 80px">RunningTime</th>';
        thHtml += '<th style="width: 80px">Log</th>';
        thHtml += '<th style="width: 80px">Operation</th>';
    } else {
        thHtml += '<th style="width: 80px">EndTime</th>';
        thHtml += '<th style="width: 80px">RunningTime</th>';
        thHtml += '<th style="width: 80px">Log</th>';
        thHtml += '<th style="width: 80px">Operation</th>';
    }
    thHtml += '</tr>';
    tHead.empty().append(thHtml);  // 装载数据

    let tBody = $("#tBody");
    let tbHtml = '';
    //遍历数据添加
    $.each(dataList, function (key, data) {
        tbHtml += '<tr>';
        tbHtml += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        tbHtml += '<td>' + data.job_id + '</td>';
        tbHtml += '<td>' + data.host_port + '</td>';
        tbHtml += '<td>' + data.project_name + '</td>';
        tbHtml += '<td>' + data.spider_name + '</td>';
        tbHtml += '<td>' + data.plan_name + '</td>';
        if (jobStatus === 'pending') {
            tbHtml += '<td>' + data.create_time + '</td>';
            tbHtml += '<td>' + data.waiting_time + '</td>';
        } else if (jobStatus === 'running') {
            tbHtml += '<td>' + data.start_time + '</td>';
            tbHtml += '<td>' + data.running_time + '</td>';
            tbHtml += '<td><a href="/job/log/' + data.vc_md5 + '" target="_blank" data-toggle="tooltip" data-placement="top" title="' + data.job_id + '">Log</a></td>';
            tbHtml += '<td><a href="/job/stop/' + data.vc_md5 + '" type="button" class="btn btn-danger">Stop</a></td>';
        } else {
            tbHtml += '<td>' + data.end_time + '</td>';
            tbHtml += '<td>' + data.running_time + '</td>';
            tbHtml += '<td><a href="/job/log/' + data.vc_md5 + '" target="_blank" data-toggle="tooltip" data-placement="top" title="' + data.job_id + '">Log</a></td>';
            tbHtml += '<td><a href="/job/delete/' + data.vc_md5 + '" type="button" class="btn btn-danger">Delete</a></td>';
        }
    });
    // 装载数据 加载事件
    tBody.empty().append(tbHtml).find('.btn-danger').click(function () {
        let msg = "确定要终止/删除吗？\n\n请确认！";
        return confirm(msg);
    });
    return tbHtml;
}

function pageSearch(event, pageNum) {
    let ajaxUrl = "/job/search";
    let searchString = $("#searchString").val();  // 得到查询条件
    let pageSize = $("#pageSize").val();  // 得到每页显示条数
    let dataType = $("#dataType").val();  // 是否关闭异常的查询条件
    if (!pageNum) {
        pageNum = 1;  // 得到显示第几页
    }
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"pageNum": pageNum, "pageSize": pageSize, "dataType": dataType, 'keywords': searchString},
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

function initDataException(dataList, pageSize, pageNum) {
    let tBody = $("#tBody");
    let is_closed = parseInt($("#dataType").val());
    let tbHtml = '';
    //遍历数据添加
    $.each(dataList, function (key, data) {
        tbHtml += '<tr>';
        tbHtml += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        tbHtml += '<td>' + data.host_port + '</td>';
        tbHtml += '<td>' + data.project_name + '</td>';
        tbHtml += '<td>' + data.spider_name + '</td>';
        tbHtml += '<td>' + data.job_id + '</td>';
        tbHtml += '<td>' + data.exc_time + '</td>';
        tbHtml += '<td>' + data.exc_level + '</td>';
        tbHtml += '<td><div style="width:80px;white-space: nowrap;text-overflow:ellipsis; overflow:hidden;">' + data.remark + '</div></td>';
        tbHtml += '<td>';
        if (is_closed === 0) {
            tbHtml += '<a type="button" class="btn btn-info client-error-edit" data-wrap="' + encodeURI(JSON.stringify(data)) + '" data-toggle="modal" data-target="#errorModal">Edit</a>';
        } else {
            tbHtml += '<a type="button" class="btn btn-danger" href="/job/exception/delete/' + data.vc_md5 + '">Delete</a>';
        }
        tbHtml += '</td>';
        tbHtml += '</tr>';
    });
    // 装载数据 加载事件
    tBody.empty().append(tbHtml).find('.btn-danger').click(function () {
        let msg = "确定要删除吗？\n\n请确认！";
        return confirm(msg);
    });
    return tbHtml;
}

function pageSearchException(event, pageNum) {
    let ajaxUrl = "/job/exception/search";
    let searchString = $("#searchString").val();  // 得到查询条件
    let pageSize = $("#pageSize").val();  // 得到每页显示条数
    let dataType = $("#dataType").val();  // 是否关闭异常的查询条件
    if (!pageNum) {
        pageNum = 1;  // 得到显示第几页
    }
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"pageNum": pageNum, "pageSize": pageSize, "dataType": dataType, 'keywords': searchString},
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
                pager.empty().append(initPage(pagination));
                pager.find('li a').click(function () {
                    pageSearch(null, $(this).attr("data-id"))
                });
                initDataException(dataList, pageSize, pageNum)
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function showModalException(event) {
    let data = JSON.parse(decodeURI($(event.relatedTarget).data('wrap')));
    let modal = $(this);
    modal.find("#vc_md5").val(data.vc_md5);
    modal.find("#host_port").val(data.host_port);
    modal.find("#project_name").val(data.project_name);
    modal.find("#spider_name").val(data.spider_name);
    modal.find("#job_id").val(data.job_id);
    modal.find("#exc_time").val(data.exc_time);
    modal.find("#exc_level").val(data.exc_level);
    modal.find("#exc_message").val(data.exc_message);
    modal.find("#is_closed").val(data.is_closed);
    modal.find("#remark").val(data.remark);
}

function hideModalException() {
    let modal = $(this);
    modal.find("#host_port").val(null);
    modal.find("#project_name").val(null);
    modal.find("#spider_name").val(null);
    modal.find("#job_id").val(null);
    modal.find("#exc_time").val(null);
    modal.find("#exc_level").val(null);
    modal.find("#exc_message").val(null);
    modal.find("#is_closed").val(false);
    modal.find("#remark").val(null);
}
