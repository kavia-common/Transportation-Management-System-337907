/**
 * Transportation Management System - Admin Panel JavaScript
 *
 * Handles all dynamic admin panel functionality including:
 * - Table data loading and pagination
 * - CRUD operations (Create, Read, Update, Delete)
 * - Shipment management with status transitions
 * - Route planning display
 * - Dashboard statistics
 *
 * All API calls use relative URLs (no hardcoded external domains).
 */

var tablename;
var elemId;
var totalNum;
var currentPage = 1;
var sortSelected = ['', '', 'selected'];
var isSort = false;
var isIncremented = false;

// Base URL derived from current location (relative)
var API_BASE = '/api/';
var ADMIN_BASE = '/admin/';

$('body').on('focus', ".datepicker_recurring_start", function () {
    $(this).datetimepicker({
        defaultDate: new Date(),
        format: 'YYYY-MM-DD HH:mm:ss',
        sideBySide: true
    });
});

// ---------------------------------------------------------------------------
// Dashboard Statistics (loaded on page init)
// ---------------------------------------------------------------------------
function loadDashboardStats() {
    $.getJSON(API_BASE + "dashboard/stats", function (stats) {
        if (stats.total_jobs !== undefined) {
            $('#statParcels').text(stats.total_jobs || 0);
            $('#statDrivers').text(stats.total_drivers || 0);
            var total = stats.total_jobs || 0;
            var delivered = stats.delivered_jobs || 0;
            var pct = total > 0 ? Math.round((delivered / total) * 100) : 0;
            $('#statCompleted').text(pct + '%');
            $('#completedBar').css('width', pct + '%').attr('aria-valuenow', pct);

            // Shipment stats
            if ($('#statShipments').length) {
                $('#statShipments').text(stats.total_shipments || 0);
            }
            if ($('#statActiveRoutes').length) {
                $('#statActiveRoutes').text(stats.active_routes || 0);
            }
        }
    }).fail(function () {
        console.log("Could not load dashboard stats");
    });
}

// Load stats when page loads
$(document).ready(function () {
    loadDashboardStats();
});

// ---------------------------------------------------------------------------
// Navigation and Page Loading
// ---------------------------------------------------------------------------
function newPage(data, l1, l2) {
    currentPage = 1;
    isSort = false;
    getData(data, l1, l2);
}

function getData(data, l1, l2) {
    if (!isSort) {
        tablename = data;
        setActiveButton(data);
        $.getJSON(API_BASE + data, function (result) {
            totalNum = result.length;
            $.getJSON(API_BASE + data + "?limit1=" + l1 + "&limit2=" + l2, function (result) {
                makeTable(result, l1, l2);
            });
        }).fail(function() {
            $('#pageContent').html('<div class="alert alert-warning m-3">Could not load data for ' + data + '</div>');
        });
    } else {
        buildLink(l1, l2);
    }
}

function getHeaders(result) {
    var headers = [];
    $.each(result, function (key, value) {
        headers.push(key);
    });
    return headers;
}

// ---------------------------------------------------------------------------
// Table Rendering
// ---------------------------------------------------------------------------
function makeTable(result, l1, l2) {
    isIncremented = false;
    var modalIndex = 0;
    $('#pageHeader').html(tablename.charAt(0).toUpperCase() + tablename.slice(1));
    $('#pageContent').css("margin-right", "15px");

    if (!result || result.length === 0) {
        var empty = '<div class="m-3"><div class="alert alert-info">No records found for ' + tablename + '.</div>';
        empty += '<button class="btn btn-primary" data-toggle="modal" data-target="#addModal"><i class="fas fa-plus"></i> Create Record</button></div>';
        // Still need to generate the add modal
        var emptyModal = makeEmptyAddModal();
        $("#pageContent").html(empty);
        $("#modals").html(emptyModal);
        return;
    }

    var table = '<div style="margin-left:5px;" class="row">';
    table += '<div class="col-xl-3 col-md-6 mb-4"><div class="card card-hover border-left-primary shadow h-10 py-2" data-toggle="modal" data-target="#addModal" style="cursor: pointer;"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Add</div><div class="h5 mb-0 font-weight-bold text-gray-800">Create Record</div></div><div class="col-auto"><i class="fas fa-plus fa-2x text-gray-300"></i></div></div></div></div></div>';
    table += '<div class="col-xl-3 col-md-6 mb-4"><div class="card border-left-success shadow h-10 py-2"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-success text-uppercase mb-1">Number of ' + tablename + '</div><div class="h5 mb-0 font-weight-bold text-gray-800">' + totalNum + '</div></div><div class="col-auto"><i class="fas fa-warehouse fa-2x text-gray-300"></i></div></div></div></div></div>';

    // Sort option for jobs and shipments
    if (tablename == 'jobs') {
        table += '<div class="col-xl-3 col-md-6 mb-4"><div class="card border-left-info shadow h-10 py-2" style="height:103px;"><div class="card-body"><div class="row no-gutters align-items-center"><div class="col mr-2"><div class="text-xs font-weight-bold text-info text-uppercase mb-1">Filter by Status</div><div class="h5 mb-0 font-weight-bold text-gray-800"><div class="form-group"><select id="selectSortOption" class="form-control" onchange="newPageSort(10,0);"><option ' + sortSelected[0] + ' value="pending">Pending</option><option value="in-transit">In Transit</option><option ' + sortSelected[1] + ' value="delivered">Delivered</option><option ' + sortSelected[2] + ' value="all">All</option></select></div></div></div><div class="col-auto" style="top:-14px;"><i class="fas fa-sort fa-2x text-gray-300"></i></div></div></div></div></div>';
    }
    table += '</div>';

    table += '<p style="margin-left:18px;">Click on a record to see full details and perform updates.</p>';
    table += '<div style="width:auto;margin:18px;" class="card border-left-warning shadow"><table class="table table-hover"><thead><tr>';

    var headers = getHeaders(result[0]);
    var modals = makeModals(result);
    var picModals = '';

    var i = 0;
    for (var header in headers) {
        if (i < 8) {
            table += '<th scope="col">' + headers[header] + '</th>';
            i++;
        }
    }
    table += '</tr></thead><tbody>';

    var picId = 1;
    $.each(result, function (key, value) {
        table += '<tr>';
        i = 0;
        for (var index in value) {
            if (i < 8) {
                var t = '' + value[index];
                if (t.toLowerCase().includes('.jpg') || t.toLowerCase().includes('.png') || t.toLowerCase().includes('.gif')) {
                    table += '<td><a style="margin-left:5px;height:30px;cursor:pointer;" data-toggle="modal" data-target="#modalPic' + picId + '" class="text-primary"><i class="fas fa-camera"></i> View</a></td>';
                    picModals += '<div class="modal fade" id="modalPic' + picId + '" tabindex="-1" role="dialog"><div class="modal-dialog" role="document"><div class="modal-content"><div class="modal-header"><h4 class="modal-title">Picture</h4><button type="button" class="close" data-dismiss="modal"><span>&times;</span></button></div><div class="modal-body"><a href="' + value[index] + '" target="_blank"><img style="display:block;width:90%;margin:auto;" src="' + value[index] + '" /></a></div><div class="modal-footer"><button type="button" class="btn btn-dark" data-dismiss="modal">Close</button></div></div></div></div>';
                    picId++;
                } else {
                    // Add status badge styling
                    var cellContent = value[index];
                    if (index === 'Status' && cellContent) {
                        var badgeClass = 'badge-secondary';
                        if (cellContent === 'Pending') badgeClass = 'badge-warning';
                        else if (cellContent === 'In Transit') badgeClass = 'badge-info';
                        else if (cellContent === 'Delivered') badgeClass = 'badge-success';
                        else if (cellContent === 'Active') badgeClass = 'badge-primary';
                        else if (cellContent === 'Available') badgeClass = 'badge-success';
                        else if (cellContent === 'Completed') badgeClass = 'badge-success';
                        cellContent = '<span class="badge ' + badgeClass + '">' + cellContent + '</span>';
                    }
                    table += '<td data-toggle="modal" data-target="#modal' + modalIndex + '" style="cursor: pointer;">' + cellContent + '</td>';
                }
                i++;
            }
        }
        table += '</tr>';
        modalIndex++;
    });

    table += '</tbody></table></div>';
    table = table.replace(/null/g, '');

    // Pagination
    var totalPages = Math.ceil(totalNum / 10);
    if (totalPages < 1) totalPages = 1;
    table += buildPagination(l1, l2, result.length, totalPages);

    $("#pageContent").html(table);
    $("#modals").html(modals + picModals);
}

function buildPagination(l1, l2, resultLength, totalPages) {
    var pag = '<nav class="mt-3 ml-3"><ul class="pagination">';
    if (l2 == 0) {
        pag += '<li class="page-item disabled"><a class="page-link"><i class="fas fa-angle-left"></i></a></li>';
    } else {
        var prevOffset = l2 - 10;
        pag += '<li class="page-item"><a class="page-link" style="cursor:pointer;" onclick="getData(\'' + tablename + '\',' + l1 + ',' + prevOffset + ');changePageNum(false);"><i class="fas fa-angle-left"></i></a></li>';
    }
    pag += '<li class="page-item disabled"><a class="page-link">Page ' + currentPage + ' of ' + totalPages + '</a></li>';
    if (resultLength < 10) {
        pag += '<li class="page-item disabled"><a class="page-link"><i class="fas fa-angle-right"></i></a></li>';
    } else {
        var nextOffset = l2 + 10;
        pag += '<li class="page-item"><a class="page-link" style="cursor:pointer;" onclick="getData(\'' + tablename + '\',' + l1 + ',' + nextOffset + ');changePageNum(true);"><i class="fas fa-angle-right"></i></a></li>';
    }
    pag += '</ul></nav>';
    return pag;
}

// ---------------------------------------------------------------------------
// Modal Generation
// ---------------------------------------------------------------------------
function makeModals(result) {
    var modal = '';
    var modalIndex = 0;
    var elemIdLocal;

    $.each(result, function (key, value) {
        modal += '<div class="modal fade" id="modal' + modalIndex + '" tabindex="-1" role="dialog">';
        modal += '<div class="modal-dialog modal-xl" role="document">';
        modal += '<div class="modal-content">';
        modal += '<div class="modal-header"><h5 class="modal-title">Update Record</h5>';
        modal += '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button></div>';
        modal += '<div class="modal-body"><form name="form' + modalIndex + '">';

        var oddCheck = 0;
        var first_iteration = true;
        for (var index in value) {
            if (first_iteration) {
                elemIdLocal = value[index];
                first_iteration = false;
                modal += '<input type="hidden" id="elemId' + modalIndex + '" value="' + elemIdLocal + '">';
            } else {
                var disabled = '';
                if (index.toLowerCase().includes('datecreated') || index.toLowerCase().includes('lastconnected') || index.toLowerCase().includes('createdat')) {
                    disabled = 'disabled="disabled"';
                }

                var fieldHtml = '';
                if (index.toLowerCase().includes('date') || index.toLowerCase().includes('lastconnected') || index.toLowerCase().includes('createdat') || index.toLowerCase().includes('updatedat')) {
                    fieldHtml = '<div class="input-group date"><input type="text" ' + disabled + ' class="form-control datepicker_recurring_start" name="' + index + '" value="' + (value[index] || '') + '" /><div class="input-group-append"><span class="input-group-text"><i class="fas fa-calendar-alt"></i></span></div></div>';
                } else if (index === 'Status') {
                    // Status dropdown
                    var statusOptions = getStatusOptions(tablename, value[index]);
                    fieldHtml = '<select class="form-control" name="' + index + '">' + statusOptions + '</select>';
                } else {
                    fieldHtml = '<input class="form-control" type="text" name="' + index + '" value="' + (value[index] || '') + '" />';
                }

                if (oddCheck % 2 == 1) {
                    modal += '<div class="row mb-2"><div class="col-sm-2"><label class="font-weight-bold">' + index + '</label></div><div class="col-sm-4">' + fieldHtml + '</div>';
                } else {
                    modal += '<div class="col-sm-2"><label class="font-weight-bold">' + index + '</label></div><div class="col-sm-4">' + fieldHtml + '</div></div>';
                }
                oddCheck++;
            }
        }
        oddCheck--;
        if (oddCheck % 2 != 0) {
            modal += '<div class="col-sm-2"></div><div class="col-sm-4"></div></div>';
        }

        modal += '</form></div>';
        modal += '<div class="modal-footer">';
        modal += '<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>';
        modal += '<button type="button" class="btn btn-danger" data-toggle="modal" onclick="getRowId(\'elemId' + modalIndex + '\');" data-target="#deleteModal" data-dismiss="modal">Delete</button>';
        modal += '<button type="button" class="btn btn-primary" data-dismiss="modal" onclick="updateRecord(' + modalIndex + ',' + elemIdLocal + ',\'' + tablename + '\');">Save changes</button>';
        modal += '</div></div></div></div>';
        modalIndex++;
    });

    // Add Modal
    var headers = getHeaders(result[0]);
    modal += buildAddModal(headers);

    // Delete Modal
    modal += '<div class="modal fade" id="deleteModal" tabindex="-1" role="dialog"><div class="modal-dialog" role="document"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Delete Record</h5><button type="button" class="close" data-dismiss="modal"><span>&times;</span></button></div><div class="modal-body"><p>Are you sure you want to delete this record?<br>This cannot be undone.</p></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button><button type="button" class="btn btn-danger" data-dismiss="modal" onclick="deleteRecord(\'' + tablename + '\');">Delete</button></div></div></div></div>';

    modal = modal.replace(/null/g, '');
    return modal;
}

function buildAddModal(headers) {
    var modal = '<div class="modal fade" id="addModal" tabindex="-1" role="dialog"><div class="modal-dialog modal-xl" role="document"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Record</h5><button type="button" class="close" data-dismiss="modal"><span>&times;</span></button></div><div class="modal-body"><form name="createForm" id="createForm">';

    var first_iteration = true;
    var oddCheck = 0;
    for (var header in headers) {
        if (first_iteration) {
            first_iteration = false;
        } else {
            var disabled = '';
            if (headers[header].toLowerCase().includes('datecreated') || headers[header].toLowerCase().includes('lastconnected') || headers[header].toLowerCase().includes('createdat') || headers[header].toLowerCase().includes('updatedat')) {
                disabled = 'disabled="disabled"';
            }

            var fieldHtml = '';
            if (headers[header].toLowerCase().includes('date') || headers[header].toLowerCase().includes('lastconnected') || headers[header].toLowerCase().includes('createdat') || headers[header].toLowerCase().includes('updatedat')) {
                fieldHtml = '<div class="input-group"><input type="text" ' + disabled + ' class="form-control datepicker_recurring_start" name="' + headers[header] + '" /><div class="input-group-append"><span class="input-group-text"><i class="fas fa-calendar-alt"></i></span></div></div>';
            } else if (headers[header] === 'Status') {
                var statusOptions = getStatusOptions(tablename, '');
                fieldHtml = '<select class="form-control" name="' + headers[header] + '">' + statusOptions + '</select>';
            } else {
                fieldHtml = '<input class="form-control" type="text" name="' + headers[header] + '" />';
            }

            if (oddCheck % 2 == 1) {
                modal += '<div class="row mb-2"><div class="col-sm-2"><label class="font-weight-bold">' + headers[header] + '</label></div><div class="col-sm-4">' + fieldHtml + '</div>';
            } else {
                modal += '<div class="col-sm-2"><label class="font-weight-bold">' + headers[header] + '</label></div><div class="col-sm-4">' + fieldHtml + '</div></div>';
            }
            oddCheck++;
        }
    }
    oddCheck--;
    if (oddCheck % 2 != 0) {
        modal += '<div class="col-sm-2"></div><div class="col-sm-4"></div></div>';
    }

    modal += '</form></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button><button type="button" class="btn btn-primary" data-dismiss="modal" onclick="createRecord(\'' + tablename + '\');">Create Record</button></div></div></div></div>';
    return modal;
}

function makeEmptyAddModal() {
    return '<div class="modal fade" id="addModal" tabindex="-1" role="dialog"><div class="modal-dialog modal-xl" role="document"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Record</h5><button type="button" class="close" data-dismiss="modal"><span>&times;</span></button></div><div class="modal-body"><p>Table schema not yet available. Please add the first record via the API.</p></div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>';
}

function getStatusOptions(table, currentVal) {
    var options = [];
    if (table === 'jobs' || table === 'shipments') {
        options = ['Pending', 'In Transit', 'Delivered'];
    } else if (table === 'routes') {
        options = ['Planned', 'Active', 'Completed', 'Cancelled'];
    } else if (table === 'vehicles') {
        options = ['Available', 'In Use', 'In Maintenance'];
    } else {
        return '<option value="' + (currentVal || '') + '">' + (currentVal || '') + '</option>';
    }
    var html = '';
    for (var i = 0; i < options.length; i++) {
        var sel = (options[i] === currentVal) ? 'selected' : '';
        html += '<option ' + sel + ' value="' + options[i] + '">' + options[i] + '</option>';
    }
    return html;
}

// ---------------------------------------------------------------------------
// CRUD Operations
// ---------------------------------------------------------------------------
function updateRecord(formId, elemId, table) {
    $('form:eq(' + formId + ') *').filter(':input').each(function () {
        if (this.value == '') { this.value = 'None'; }
        if (this.value == ' ') { this.value = 'None'; }
    });
    var str = $('form:eq(' + formId + ')').serialize();
    str = str.replace(/null/g, 'None');
    $.ajax({
        method: "PUT",
        url: API_BASE + table + "/" + elemId + "?" + str,
        success: function (dat) {
            getData(table, 10, 0);
        },
        error: function () {
            alert('Failed to update record');
        }
    });
}

function deleteRecord(table) {
    $.ajax({
        method: "DELETE",
        url: API_BASE + table + "/" + elemId,
        success: function (dat) {
            getData(table, 10, 0);
        },
        error: function () {
            alert('Failed to delete record');
        }
    });
}

function createRecord(table) {
    $('form[name="createForm"] *').filter(':input').each(function () {
        if (this.value == '') { this.value = 'None'; }
    });
    var str = $('form[name="createForm"]').serialize();
    str = str.replace(/null/g, 'None');
    $.ajax({
        method: "POST",
        url: API_BASE + table + "?" + str,
        success: function (dat) {
            getData(table, 10, 0);
        },
        error: function () {
            alert('Failed to create record');
        }
    });
}

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------
function getRowId(elemModal) {
    elemId = $('#' + elemModal).val();
}

function setActiveButton(id) {
    $(".nav-item").removeClass("active");
    $("#nav-" + id).addClass("active");
}

function changePassword() {
    var oldpas = $('#oldPassword').val();
    var newpas1 = $('#newPassword1').val();
    var newpas2 = $('#newPassword2').val();
    if (newpas1 == newpas2) {
        $.ajax({
            method: "PUT",
            url: ADMIN_BASE + "changepassword?oldPassowrd=" + oldpas + "&newPassword=" + newpas1,
            success: function (dat) {
                if (dat.Status == 'Error') {
                    $('#changePasswordMessage').text(dat.Message);
                } else {
                    $('#changePasswordModal').modal('toggle');
                    alert(dat.Message);
                }
                $('#oldPassword').val('');
                $('#newPassword1').val('');
                $('#newPassword2').val('');
            }
        });
    } else {
        $('#changePasswordMessage').text("New passwords don't match.");
    }
}

function changePageNum(increment) {
    if (!isIncremented) {
        isIncremented = true;
        if (increment) {
            currentPage++;
        } else {
            currentPage--;
        }
    }
}

function newPageSort(l1, l2) {
    currentPage = 1;
    buildLink(l1, l2);
}

function buildLink(l1, l2) {
    isSort = true;
    var e = document.getElementById("selectSortOption");
    var option = e.options[e.selectedIndex].value;
    if (option == 'all') {
        isSort = false;
        sortSelected = ['', '', 'selected'];
        getData('jobs', 10, 0);
    } else {
        var link = 'jobs/' + option;
        tablename = 'jobs';
        setActiveButton('jobs');
        $.getJSON(API_BASE + link.toLowerCase(), function (result) {
            totalNum = result.length;
            $.getJSON(API_BASE + link.toLowerCase() + "?limit1=" + l1 + "&limit2=" + l2, function (result) {
                makeTable(result, l1, l2);
            });
        });
    }
}
