function getSystemStatus() {
    let ajaxUrl = "/system/detail/status";
    let tBody = $("#tBodyStatus");
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (data) {
                if (!data) {
                    return  // 失败，请重试
                }
                let html = '<tr>';
                html += '<td>' + data.cpu + '</td>';
                html += '<td>' + data.virtual_memory + '</td>';
                html += '<td>' + data.swap_memory + '</td>';
                html += '<td>' + data.disk_usage + '</td>';
                html += '<td>' + data.disk_io_read + '</td>';
                html += '<td>' + data.disk_io_write + '</td>';
                html += '<td>' + data.net_io_sent + '</td>';
                html += '<td>' + data.net_io_receive + '</td>';
                html += "</tr>";
                // 装载数据
                tBody.empty().append(html);
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
    let html = '';
    //遍历数据添加
    $.each(dataList, function (key, data) {
        html += '<tr data-id="' + data.vc_md5 + '">';
        html += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        html += '<td>' + data.host_port + '</td>';
        html += '<td>' + data.exc_time + '</td>';
        html += '<td>' + data.exc_level + '</td>';
        html += '<td><div style="width:80px;white-space: nowrap;text-overflow:ellipsis; overflow:hidden;">' + data.exc_message + '</div></td>';
        html += '<td><div style="width:120px;white-space: nowrap;text-overflow:ellipsis; overflow:hidden;">' + data.remark + '</div></td>';
        html += '<td>';
        if (is_closed === 0) {
            html += '<a type="button" class="btn btn-info client-error-edit" data-wrap="' + encodeURI(JSON.stringify(data)) + '" data-toggle="modal" data-target="#errorModal">Close</a>';
        } else {
            html += '<a type="button" class="btn btn-danger" href="/system/exception/delete/' + data.vc_md5 + '">Delete</a>';
        }
        html += '</td>';
        html += '</tr>';
    });
    // 装载数据 加载事件
    tBody.empty().append(html).find('.btn-danger').click(function () {
        let msg = "确定要删除吗？\n\n请确认！";
        return confirm(msg);
    });
    return html;
}

function pageSearchException(event, pageNum) {
    let ajaxUrl = "/system/exception/search";
    let searchString = $("#searchString").val();  // 得到查询条件
    let pageSize = $("#pageSize").val();  // 得到每页显示条数
    let dataType = $("#dataType").val();  // 是否关闭异常的查询条件
    let dataID = $("#tBodyStatus").attr("data-id");
    if (!pageNum) {
        pageNum = 1;  // 得到显示第几页
    }
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {
                "pageNum": pageNum,
                "pageSize": pageSize,
                "dataType": dataType,
                "dataID": dataID,
                "keywords": searchString
            },
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
    modal.find("#exc_time").val(data.exc_time);
    modal.find("#exc_level").val(data.exc_level);
    modal.find("#exc_message").val(data.exc_message);
    modal.find("#is_closed").val(data.is_closed);
    modal.find("#remark").val(data.remark);
}

function hideModalException() {
    let modal = $(this);
    modal.find("#host_port").val(null);
    modal.find("#exc_time").val(null);
    modal.find("#exc_level").val(null);
    modal.find("#exc_message").val(null);
    modal.find("#is_closed").val(false);
    modal.find("#remark").val(null);
}