function setProjects(event, projectName, versionName, spiderName) {
    let ajaxUrl = "/plan/projects";
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
            success: function (dataList) {
                let html = '';
                $.each(dataList, function (key, value) {
                    html += '<option value="' + value + '">' + value + '</option>';
                });
                let select = $('#project_name');
                select.empty().append(html);
                if (projectName && select.find("option[value='" + projectName + "']")) {
                    select.find("option[value='" + projectName + "']").attr("selected", true);
                } else {
                    select.find("option").first().attr("selected", true);
                }
                setVersions(null, projectName, versionName, spiderName);
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function setVersions(event, projectName, versionName, spiderName) {
    let ajaxUrl = "/plan/versions";
    if (!projectName) {
        projectName = $("#project_name").val();  // # option:selected
    }
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"projectName": projectName},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (dataList) {
                let html = '';
                $.each(dataList, function (key, value) {
                    html += '<option value="' + value + '">' + value + '</option>';
                });
                let select = $('#version_name');
                select.empty().append(html);
                if (versionName && select.find("option[value='" + versionName + "']")) {
                    select.find("option[value='" + versionName + "']").attr("selected", true);
                } else {
                    select.find("option").first().attr("selected", true);
                }
                setSpiders(null, projectName, versionName, spiderName);
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function setSpiders(event, projectName, versionName, spiderName) {
    let ajaxUrl = "/plan/spiders";
    if (!projectName) {
        projectName = $("#project_name").val();  // # option:selected
    }
    if (!versionName) {
        versionName = $("#version_name").val();  // # option:selected
    }
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"projectName": projectName, "versionName": versionName},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (dataList) {
                let html = '';
                $.each(dataList, function (key, value) {
                    html += '<option value="' + value + '">' + value + '</option>';
                });
                let select = $('#spider_name');
                select.empty().append(html);
                if (spiderName && select.find("option[value='" + spiderName + "']")) {
                    select.find("option[value='" + spiderName + "']").attr("selected", true);
                } else {
                    select.find("option").first().attr("selected", true);
                }
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function setClients(event, clientAddress) {
    let ajaxUrl = "/plan/clients";
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
            success: function (dataList) {
                let html = '<option value="auto">Auto</option>';
                $.each(dataList, function (key, value) {
                    html += '<option value="' + value + '">' + value + '</option>';
                });
                let select = $('#host_port');
                select.empty().append(html);
                if (clientAddress && select.find("option[value='" + clientAddress + "']")) {
                    select.find("option[value='" + clientAddress + "']").attr("selected", true);
                } else {
                    select.find("option").first().attr("selected", true);
                }
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function initData(dataList, pageSize, pageNum) {
    let tbHtml = '';
    //遍历数据添加
    $.each(dataList, function (key, data) {
        tbHtml += '<tr data-id="' + data.vc_md5 + '">';
        tbHtml += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        tbHtml += '<td>' + data.plan_name + '</td>';
        tbHtml += '<td>' + data.project_name + '</td>';
        tbHtml += '<td>' + data.spider_name + '</td>';
        tbHtml += '<td>' + data.host_port + '</td>';
        tbHtml += '<td>' + data.priority + '</td>';
        tbHtml += '<td>' + data.cron_exp + '</td>';
        tbHtml += '<td>' + data.is_enabled + '</td>';
        tbHtml += '<td>';
        tbHtml += '<a type="button" class="btn btn-info" data-wrap="' + encodeURI(JSON.stringify(data)) + '" data-toggle="modal" data-target="#planModal">Edit</a>';
        tbHtml += '<a type="button" class="btn btn-danger" href="/plan/delete/' + data.vc_md5 + '">Delete</a>';
        tbHtml += '</td>';
        tbHtml += '</tr>';
    });
    // 装载数据 加载事件
    $("#tBody").empty().append(tbHtml).find('.btn-danger').click(function () {
        let msg = "确定要删除吗？\n\n请确认！";
        return confirm(msg);
    });
}

function pageSearch(event, pageNum) {
    let ajaxUrl = "/plan/search";
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
                pager.empty().append(initPage(pagination));
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

function showModel(event) {
    let modal = $(this);
    let wrap = $(event.relatedTarget).data('wrap');
    if (!wrap) {
        modal.find('.modal-title').text("Create Plan");  // 创建计划
        modal.find("#submit").text("Create");  // 创建
        // 将input元素设置为readonly
        modal.find('#plan_name').removeAttr("readonly");
        // 重置相关值
        setProjects(null, null, null, null);
        setClients(null, null);
        // modal.find("#project_name").change();
        modal.find("#plan_name").val(null);
        modal.find("#exec_args").val(null);
        modal.find("#priority").val('0');
        modal.find("#cron_exp").val(null);
        modal.find("#is_enabled").val(true);
        modal.find("#act").val('add');
        return
    }
    let data = JSON.parse(decodeURI(wrap));

    modal.find('.modal-title').text("Update Plan");  // 更新计划
    modal.find("#submit").text("Update");  // 更新
    // 将input元素设置为readonly
    modal.find('#plan_name').attr("readonly", "readonly");
    setProjects(null, data.project_name, data.version_name, data.spider_name);
    setClients(null, data.host_port);
    modal.find("#plan_name").val(data.plan_name);
    modal.find("#exec_args").val(data.job_args);
    modal.find("#priority").val(data.priority);
    modal.find("#cron_exp").val(data.cron_exp);
    modal.find("#is_enabled").val(data.is_enabled);
    modal.find("#act").val('upd');
}
