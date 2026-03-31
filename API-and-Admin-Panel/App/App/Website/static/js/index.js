/**
 * Transportation Management System - Customer Website JavaScript
 *
 * Provides parcel tracking functionality using relative API URLs.
 * Removed external Google Maps dependency for local development.
 */

// PUBLIC_INTERFACE
/**
 * Track a parcel by its tracking ID.
 * Fetches driver location from the local API and displays results.
 */
function getLocation() {
    var trackingID = document.getElementById("trackingID").value.trim();
    if (trackingID === "") {
        alert("Please enter a valid tracking number!");
        return false;
    }

    var resultPanel = document.querySelector(".mypanel");
    var mapDiv = document.getElementById("googleMap");

    resultPanel.innerHTML = '<div class="text-white"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';

    // Try tracking as a job first (AQ prefix)
    $.getJSON("/api/jobs/" + trackingID + "/location", function (data) {
        if (data && data.length > 0 && !data[0].Error) {
            var driver = data[0];
            var html = '<div class="card" style="background:rgba(255,255,255,0.15);border:none;">';
            html += '<div class="card-body text-white">';
            html += '<h5 class="card-title"><i class="fas fa-check-circle text-success"></i> Parcel Found!</h5>';
            html += '<p><strong>Your driver:</strong> ' + (driver.FirstName || 'N/A') + '</p>';
            if (driver.Location) {
                var loc = driver.Location.split(",");
                html += '<p><strong>Current Location:</strong> ' + driver.Location + '</p>';
            }
            html += '<p class="mb-0"><small>Tracking ID: ' + trackingID + '</small></p>';
            html += '</div></div>';
            resultPanel.innerHTML = html;

            // Display map if available
            if (mapDiv && driver.Location) {
                var coords = driver.Location.split(",");
                mapDiv.innerHTML = '<div class="text-center p-5 text-white">' +
                    '<i class="fas fa-map-marker-alt fa-3x mb-3"></i>' +
                    '<h4>Driver Location</h4>' +
                    '<p>Latitude: ' + coords[0].trim() + '<br>Longitude: ' + coords[1].trim() + '</p>' +
                    '</div>';
            }
        } else {
            // Try shipment tracking
            tryShipmentTracking(trackingID, resultPanel, mapDiv);
        }
    }).fail(function () {
        // Try shipment tracking as fallback
        tryShipmentTracking(trackingID, resultPanel, mapDiv);
    });
}

function tryShipmentTracking(trackingNumber, resultPanel, mapDiv) {
    $.getJSON("/api/shipments/track/" + trackingNumber, function (data) {
        if (data && data.Shipment) {
            var s = data.Shipment;
            var html = '<div class="card" style="background:rgba(255,255,255,0.15);border:none;">';
            html += '<div class="card-body text-white">';
            html += '<h5 class="card-title"><i class="fas fa-check-circle text-success"></i> Shipment Found!</h5>';
            html += '<p><strong>Tracking #:</strong> ' + s.TrackingNumber + '</p>';

            // Status with colored badge
            var badgeClass = 'warning';
            if (s.Status === 'In Transit') badgeClass = 'info';
            else if (s.Status === 'Delivered') badgeClass = 'success';
            html += '<p><strong>Status:</strong> <span class="badge badge-' + badgeClass + '">' + s.Status + '</span></p>';

            html += '<p><strong>From:</strong> ' + s.SenderCity + ' &rarr; <strong>To:</strong> ' + s.ReceiverCity + '</p>';
            html += '<p><strong>Description:</strong> ' + (s.Description || 'N/A') + '</p>';

            if (data.Driver) {
                html += '<p><strong>Driver:</strong> ' + data.Driver.FirstName + ' ' + (data.Driver.LastName || '') + '</p>';
                if (data.Driver.Location) {
                    html += '<p><strong>Driver Location:</strong> ' + data.Driver.Location + '</p>';
                }
            }

            if (s.EstimatedDelivery) {
                html += '<p><strong>Estimated Delivery:</strong> ' + s.EstimatedDelivery + '</p>';
            }
            if (s.ActualDelivery) {
                html += '<p><strong>Delivered:</strong> ' + s.ActualDelivery + '</p>';
            }

            html += '</div></div>';
            resultPanel.innerHTML = html;

            if (mapDiv) {
                mapDiv.innerHTML = '<div class="text-center p-4 text-white">' +
                    '<i class="fas fa-shipping-fast fa-3x mb-3"></i>' +
                    '<h5>' + s.SenderCity + ' &rarr; ' + s.ReceiverCity + '</h5>' +
                    '<p>Status: ' + s.Status + '</p>' +
                    '</div>';
            }
        } else {
            resultPanel.innerHTML = '<div class="alert alert-warning">No shipment found with that tracking number.</div>';
            if (mapDiv) mapDiv.innerHTML = '';
        }
    }).fail(function () {
        resultPanel.innerHTML = '<div class="alert alert-danger">Could not find any shipment with tracking number: ' + trackingNumber + '</div>';
        if (mapDiv) mapDiv.innerHTML = '';
    });
}
