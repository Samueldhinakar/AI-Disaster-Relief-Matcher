import React from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

function LiveDisasterMap({ resources = [], requests = [] }) {

  const defaultCenter = [11.0168, 76.9558];

  return (
    <div className="map-page">

      <div className="map-header">
        <div>
          <h2>Live Disaster Map</h2>
          <p>
            View disaster requests and available resources on the map.
          </p>
        </div>

        <div className="map-legend">
          <span>
            <i className="legend-dot critical"></i>
            Critical Request
          </span>

          <span>
            <i className="legend-dot request"></i>
            Rescue Request
          </span>

          <span>
            <i className="legend-dot resource"></i>
            Available Resource
          </span>
        </div>
      </div>

      <div className="map-container">

        <MapContainer
          center={defaultCenter}
          zoom={7}
          scrollWheelZoom={true}
          style={{ height: "100%", width: "100%" }}
        >

          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* RESCUE REQUESTS */}

          {requests.map((request) => {

            if (
              request.latitude === null ||
              request.longitude === null ||
              request.latitude === undefined ||
              request.longitude === undefined
            ) {
              return null;
            }

            const isCritical = request.urgency === "Critical";

            return (
              <CircleMarker
                key={`request-${request.id}`}
                center={[
                  Number(request.latitude),
                  Number(request.longitude)
                ]}
                radius={isCritical ? 12 : 9}
                pathOptions={{
                  color: isCritical ? "#dc2626" : "#f59e0b",
                  fillColor: isCritical ? "#ef4444" : "#f59e0b",
                  fillOpacity: 0.8
                }}
              >

                <Popup>

                  <div className="map-popup">

                    <h3>🚨 Rescue Request</h3>

                    <p>
                      <strong>Resource:</strong>{" "}
                      {request.name}
                    </p>

                    <p>
                      <strong>Type:</strong>{" "}
                      {request.type}
                    </p>

                    <p>
                      <strong>Quantity:</strong>{" "}
                      {request.quantity} {request.unit}
                    </p>

                    <p>
                      <strong>Urgency:</strong>{" "}
                      {request.urgency}
                    </p>

                    <p>
                      <strong>Location:</strong>{" "}
                      {request.location}
                    </p>

                    <p>
                      <strong>Rescue Team:</strong>{" "}
                      {request.team}
                    </p>

                  </div>

                </Popup>

              </CircleMarker>
            );
          })}


          {/* DONOR RESOURCES */}

          {resources.map((resource) => {

            if (
              resource.latitude === null ||
              resource.longitude === null ||
              resource.latitude === undefined ||
              resource.longitude === undefined
            ) {
              return null;
            }

            return (
              <CircleMarker
                key={`resource-${resource.id}`}
                center={[
                  Number(resource.latitude),
                  Number(resource.longitude)
                ]}
                radius={9}
                pathOptions={{
                  color: "#16a34a",
                  fillColor: "#22c55e",
                  fillOpacity: 0.8
                }}
              >

                <Popup>

                  <div className="map-popup">

                    <h3>📦 Available Resource</h3>

                    <p>
                      <strong>Resource:</strong>{" "}
                      {resource.name}
                    </p>

                    <p>
                      <strong>Type:</strong>{" "}
                      {resource.type}
                    </p>

                    <p>
                      <strong>Quantity:</strong>{" "}
                      {resource.quantity} {resource.unit}
                    </p>

                    <p>
                      <strong>Location:</strong>{" "}
                      {resource.location}
                    </p>

                    <p>
                      <strong>Provider:</strong>{" "}
                      {resource.provider}
                    </p>

                    <p>
                      <strong>Status:</strong>{" "}
                      {resource.status}
                    </p>

                  </div>

                </Popup>

              </CircleMarker>
            );
          })}

        </MapContainer>

      </div>

    </div>
  );
}

export default LiveDisasterMap;