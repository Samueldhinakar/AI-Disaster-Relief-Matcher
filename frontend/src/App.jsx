import React, { useEffect, useState } from "react";
import LiveDisasterMap from "./LiveDisasterMap";
import {
  AlertTriangle, BrainCircuit, CheckCircle2, Droplets, HeartPulse,
  MapPin, Package, RefreshCw, Shield, Truck, Users, Utensils,
  History, Clock
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "/api";

const emptyForm = {
  type: "Food",
  name: "",
  quantity: "",
  unit: "kg",
  urgency: "High",
  location: "",
  latitude: "",
  longitude: "",
  provider: ""
};

function urgencyClass(value) {
  return value.toLowerCase();
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function App() {
  const [tab, setTab] = useState("dashboard");
  const [resourceForm, setResourceForm] = useState(emptyForm);
  const [requestForm, setRequestForm] = useState({
    ...emptyForm,
    provider: "",
    team: ""
  });
  const [resources, setResources] = useState([]);
  const [requests, setRequests] = useState([]);
  const [allRequests, setAllRequests] = useState([]);
  const [matches, setMatches] = useState([]);
  const [history, setHistory] = useState([]);
  const [message, setMessage] = useState("");

  const loadData = async () => {
  try {
    const [r, q, allQ, m, h] = await Promise.all([
      fetch(`${API}/resources`).then(x => x.json()),
      fetch(`${API}/requests`).then(x => x.json()),
      fetch(`${API}/requests/all`).then(x => x.json()),
      fetch(`${API}/matches`).then(x => x.json()),
      fetch(`${API}/history`).then(x => x.json())
    ]);

    setResources(r);
    setRequests(q);
    setAllRequests(allQ);
    setMatches(m);
    setHistory(h);
  } catch {
    setMessage("Backend is not running. Start Flask first.");
  }
};

  useEffect(() => {
    loadData();
  }, []);

  const submitResource = async (e) => {
    e.preventDefault();

    const payload = { ...resourceForm };
    payload.latitude = payload.latitude ? Number(payload.latitude) : null;
    payload.longitude = payload.longitude ? Number(payload.longitude) : null;
    payload.quantity = Number(payload.quantity);

    const response = await fetch(`${API}/resources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    setMessage(data.message || data.error);

    if (response.ok) {
      setResourceForm(emptyForm);
      await loadData();
    }
  };

  const submitRequest = async (e) => {
    e.preventDefault();

    const payload = {
      ...requestForm,
      quantity: Number(requestForm.quantity),
      latitude: requestForm.latitude
        ? Number(requestForm.latitude)
        : null,
      longitude: requestForm.longitude
        ? Number(requestForm.longitude)
        : null
    };

    const response = await fetch(`${API}/requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    setMessage(data.message || data.error);

    if (response.ok) {
      setRequestForm({
        ...emptyForm,
        provider: "",
        team: ""
      });

      await loadData();
    }
  };

  const runAI = async () => {
    setMessage(
      "AI matching engine is analyzing resources and requests..."
    );

    try {
      await fetch(`${API}/matches/run`, {
        method: "POST"
      });

      await loadData();

      setMessage("AI matching completed.");
      setTab("matches");
    } catch {
      setMessage("Could not connect to the AI matching engine.");
    }
  };

  const confirmMatch = async (match) => {
    const response = await fetch(
      `${API}/matches/${match.request.id}/confirm`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resource_id: match.resource.id,
          ai_score: match.score
        })
      }
    );

    const data = await response.json();

    setMessage(data.message || data.error);

    await loadData();

    if (response.ok) {
      setTab("history");
    }
  };
  const updateRequestStatus = async (requestId, status) => {
  try {
    const response = await fetch(
      `${API}/requests/${requestId}/status`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status })
      }
    );

    const data = await response.json();

    setMessage(data.message || data.error);

    if (response.ok) {
      await loadData();
    }
  } catch {
    setMessage("Could not update request status.");
  }
};
  const resetDemo = async () => {
    await fetch(`${API}/reset`, {
      method: "POST"
    });

    setMessage("Demo data and match history cleared.");
    await loadData();
  };

  const stats = {
    resources: resources.length,
    requests: requests.length,
    matches: matches.length,
    critical: requests.filter(
      x => x.urgency === "Critical"
    ).length
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Shield size={24} />
          </div>

          <div>
            <h1>ReliefMatch AI</h1>
            <span>Disaster Relief Resource Matcher</span>
          </div>
        </div>

        <div className="status">
          <span className="dot"></span>
          System Online
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <button
            className={tab === "dashboard" ? "active" : ""}
            onClick={() => setTab("dashboard")}
          >
            Dashboard
          </button>

          <button
            className={tab === "donor" ? "active" : ""}
            onClick={() => setTab("donor")}
          >
            Donor Resources
          </button>

          <button
            className={tab === "team" ? "active" : ""}
            onClick={() => setTab("team")}
          >
            Rescue Requests
          </button>

          <button
            className={tab === "matches" ? "active" : ""}
            onClick={() => setTab("matches")}
          >
            AI Matches
          </button>
          <button onClick={() => setTab("map")}>
          🗺️ Live Disaster Map
          </button>
          <button
  className={tab === "inventory" ? "active" : ""}
  onClick={() => {
    loadData();
    setTab("inventory");
  }}
>
  📦 Resource Inventory
</button>

<button
  className={tab === "tracking" ? "active" : ""}
  onClick={() => {
    loadData();
    setTab("tracking");
  }}
>
  📋 Request Tracking
</button>

          <button
            className={tab === "history" ? "active" : ""}
            onClick={() => {
              loadData();
              setTab("history");
            }}
          >
            <History size={16} />
            Match History
          </button>

          <button onClick={loadData}>
            <RefreshCw size={16} />
            Refresh
          </button>

          <button
            className="danger-link"
            onClick={resetDemo}
          >
            Reset Demo
          </button>
        </aside>

        <main className="main">
          {message && (
            <div className="message">
              {message}
            </div>
          )}

          {tab === "dashboard" && (
            <>
              <section className="hero">
                <div>
                  <p className="eyebrow">
                    AI-POWERED EMERGENCY COORDINATION
                  </p>

                  <h2>
                    Connect urgent needs with available relief
                    resources.
                  </h2>

                  <p>
                    Donors post what they can provide. Rescue
                    teams post what they need. The matching
                    engine compares resource type, quantity,
                    urgency and location.
                  </p>

                  <button
                    className="primary"
                    onClick={runAI}
                  >
                    <BrainCircuit size={18} />
                    Run AI Matching
                  </button>
                </div>

                <div className="hero-art">
                  <AlertTriangle size={90} />
                </div>
              </section>

              <div className="stats">
                <Stat
                  icon={<Package />}
                  label="Available Resources"
                  value={stats.resources}
                />

                <Stat
                  icon={<AlertTriangle />}
                  label="Open Requests"
                  value={stats.requests}
                />

                <Stat
                  icon={<BrainCircuit />}
                  label="AI Matches"
                  value={stats.matches}
                />

                <Stat
                  icon={<HeartPulse />}
                  label="Critical Requests"
                  value={stats.critical}
                />
              </div>

              <section className="two-col">
                <div className="card">
                  <h3>How the system works</h3>

                  <Step
                    n="1"
                    title="Donor posts resource"
                    text="Food, water, medicine, shelter or other available items."
                  />

                  <Step
                    n="2"
                    title="Rescue team posts request"
                    text="Required item, quantity, urgency and affected location."
                  />

                  <Step
                    n="3"
                    title="AI calculates matches"
                    text="The engine scores quantity, urgency, type and location."
                  />

                  <Step
                    n="4"
                    title="Team confirms match"
                    text="Confirmed resources are saved in Match History and stock is reduced."
                  />
                </div>

                <div className="card">
                  <h3>Resource categories</h3>

                  <div className="category-grid">
                    <Category icon={<Utensils />} name="Food" />
                    <Category icon={<Droplets />} name="Water" />
                    <Category icon={<HeartPulse />} name="Medicine" />
                    <Category icon={<Truck />} name="Transport" />
                    <Category icon={<Users />} name="Shelter" />
                    <Category icon={<Package />} name="Other" />
                  </div>
                </div>
              </section>
            </>
          )}

          {tab === "donor" && (
            <FormPage
              title="Post Available Resource"
              subtitle="Donors and organizations can register resources they can provide."
              onSubmit={submitResource}
              form={resourceForm}
              setForm={setResourceForm}
              button="Post Resource"
              providerLabel="Donor / Organization"
              providerField="provider"
            />
          )}

          {tab === "team" && (
            <FormPage
              title="Post Rescue Request"
              subtitle="Rescue teams can submit urgent requirements from affected areas."
              onSubmit={submitRequest}
              form={requestForm}
              setForm={setRequestForm}
              button="Post Request"
              providerLabel="Rescue Team Name"
              providerField="team"
            />
          )}

          {tab === "matches" && (
  <section>
    <div className="page-heading">
      <div>
        <p className="eyebrow">
          INTELLIGENT RESOURCE ALLOCATION
        </p>

        <h2>AI Match Results</h2>

        <p>
          Matches are generated using an explainable scoring model.
          Multiple donors can contribute to the same rescue request.
        </p>
      </div>

      <button
        className="primary"
        onClick={runAI}
      >
        <BrainCircuit size={18} />
        Re-run AI
      </button>
    </div>

    {matches.length === 0 ? (
      <div className="empty">
        <BrainCircuit size={42} />

        <h3>No matches yet</h3>

        <p>
          Post at least one resource and one request
          with the same category.
        </p>
      </div>
    ) : (
      <div className="match-list">
        {matches.map((m, index) => (
          <div
            className="match-card"
            key={`${m.request.id}-${m.resource.id}-${index}`}
          >
            <div className="match-score">
              {m.score}
              <small>%</small>
            </div>

            <div className="match-main">

              <div className="match-head">
                <span
                  className={`urgency ${urgencyClass(
                    m.request.urgency
                  )}`}
                >
                  {m.request.urgency}
                </span>

                <span className="type">
                  {m.request.type}
                </span>
              </div>

              <h3>
                {m.request.name} needed by{" "}
                {m.request.team}
              </h3>

              <p>
                <strong>Request:</strong>{" "}
                {m.request.quantity}{" "}
                {m.request.unit}
                {" • "}
                {m.request.location}
              </p>

              <p>
                <strong>Donor:</strong>{" "}
                {m.resource.provider}
              </p>

              <p>
                <strong>Available:</strong>{" "}
                {m.resource.quantity}{" "}
                {m.resource.unit}
              </p>

              <p className="reason">
                <MapPin size={15} />
                {m.reason}
              </p>
            </div>

            <button
              className="confirm"
              onClick={() => confirmMatch(m)}
            >
              <CheckCircle2 size={17} />
              Confirm Donor
            </button>
          </div>
        ))}
      </div>
    )}
  </section>
)}
          {tab === "map" && (
              <LiveDisasterMap
                  resources={resources}
                  requests={requests}
              />
         )}
         {tab === "inventory" && (
  <InventoryPage resources={resources} />
)}
         {tab === "tracking" && (
  <RequestTrackingPage
    requests={allRequests}
    updateRequestStatus={updateRequestStatus}
  />
)}
          {tab === "history" && (
            <HistoryPage history={history} />
          )}

          {(tab === "dashboard" ||
            tab === "donor" ||
            tab === "team") && (
            <section className="tables">
              <div className="card">
                <h3>Recent Available Resources</h3>

                {resources.length === 0 ? (
                  <p className="muted">
                    No resources posted.
                  </p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Resource</th>
                          <th>Quantity</th>
                          <th>Urgency</th>
                          <th>Location</th>
                          <th>Donor</th>
                        </tr>
                      </thead>

                      <tbody>
                        {resources.slice(0, 8).map(r => (
                          <tr key={r.id}>
                            <td>{r.name}</td>
                            <td>
                              {r.quantity} {r.unit}
                            </td>
                            <td>
                              <span
                                className={`urgency ${urgencyClass(
                                  r.urgency
                                )}`}
                              >
                                {r.urgency}
                              </span>
                            </td>
                            <td>{r.location}</td>
                            <td>{r.provider}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="card">
                <h3>Open Rescue Requests</h3>

                {requests.length === 0 ? (
                  <p className="muted">
                    No requests posted.
                  </p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Need</th>
                          <th>Quantity</th>
                          <th>Urgency</th>
                          <th>Location</th>
                          <th>Team</th>
                        </tr>
                      </thead>

                      <tbody>
                        {requests.slice(0, 8).map(r => (
                          <tr key={r.id}>
                            <td>{r.name}</td>
                            <td>
                              {r.quantity} {r.unit}
                            </td>
                            <td>
                              <span
                                className={`urgency ${urgencyClass(
                                  r.urgency
                                )}`}
                              >
                                {r.urgency}
                              </span>
                            </td>
                            <td>{r.location}</td>
                            <td>{r.team}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function HistoryPage({ history }) {
  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            PREVIOUS RESOURCE ALLOCATIONS
          </p>

          <h2>Match History</h2>

          <p>
            Previously confirmed AI resource matches are
            stored here for tracking and reference.
          </p>
        </div>
      </div>

      {history.length === 0 ? (
        <div className="empty">
          <History size={45} />
          <h3>No match history yet</h3>
          <p>
            Confirm an AI match and it will appear here.
          </p>
        </div>
      ) : (
        <div className="history-list">
          {history.map(item => (
            <div
              className="history-card"
              key={item.id}
            >
              <div className="history-icon">
                <CheckCircle2 size={25} />
              </div>

              <div className="history-content">
                <div className="history-top">
                  <div>
                    <span
                      className={`urgency ${urgencyClass(
                        item.urgency
                      )}`}
                    >
                      {item.urgency}
                    </span>

                    <span className="type">
                      {item.resource_type}
                    </span>
                  </div>

                  <div className="history-score">
                    <BrainCircuit size={15} />
                    AI Score: {item.ai_score}%
                  </div>
                </div>

                <h3>{item.resource_name}</h3>

                <div className="history-grid">
                  <div>
                    <span>Requested</span>
                    <strong>
                      {item.requested_quantity}{" "}
                      {item.unit}
                    </strong>
                  </div>

                  <div>
                    <span>Supplied</span>
                    <strong>
                      {item.supplied_quantity}{" "}
                      {item.unit}
                    </strong>
                  </div>

                  <div>
                    <span>Donor</span>
                    <strong>{item.donor}</strong>
                  </div>

                  <div>
                    <span>Rescue Team</span>
                    <strong>{item.rescue_team}</strong>
                  </div>

                  <div>
                    <span>Location</span>
                    <strong>
                      <MapPin size={14} />
                      {item.location}
                    </strong>
                  </div>

                  <div>
                    <span>Matched At</span>
                    <strong>
                      <Clock size={14} />
                      {formatDate(item.matched_at)}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
function InventoryPage({ resources }) {
  const getStockStatus = quantity => {
    if (quantity <= 0) {
      return {
        text: "Out of Stock",
        className: "stock-out"
      };
    }

    if (quantity <= 20) {
      return {
        text: "Low Stock",
        className: "stock-low"
      };
    }

    return {
      text: "Available",
      className: "stock-available"
    };
  };

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">RESOURCE MANAGEMENT</p>
          <h2>Resource Inventory</h2>
          <p>
            View currently available relief resources and their stock levels.
          </p>
        </div>
      </div>

      {resources.length === 0 ? (
        <div className="empty">
          <Package size={42} />
          <h3>No resources available</h3>
          <p>Donors can post resources from the Donor Resources page.</p>
        </div>
      ) : (
        <div className="inventory-grid">
          {resources.map(resource => {
            const stock = getStockStatus(Number(resource.quantity));

            return (
              <div className="inventory-card card" key={resource.id}>
                <div className="inventory-icon">
                  <Package size={25} />
                </div>

                <div className="inventory-content">
                  <div className="inventory-top">
                    <span className="type">
                      {resource.type}
                    </span>

                    <span className={`stock-status ${stock.className}`}>
                      {stock.text}
                    </span>
                  </div>

                  <h3>{resource.name}</h3>

                  <div className="inventory-quantity">
                    <strong>
                      {resource.quantity}
                    </strong>

                    <span>{resource.unit}</span>
                  </div>

                  <p>
                    <strong>Donor:</strong>{" "}
                    {resource.provider}
                  </p>

                  <p>
                    <MapPin size={14} />
                    {resource.location}
                  </p>

                  <span
                    className={`urgency ${urgencyClass(
                      resource.urgency
                    )}`}
                  >
                    {resource.urgency}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
function RequestTrackingPage({
  requests,
  updateRequestStatus
}) {
  const getStatusClass = status => {
    if (status === "Delivered") return "status-delivered";
    if (status === "In Transit") return "status-transit";
    if (status === "Matched") return "status-matched";

    return "status-open";
  };

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">RELIEF REQUEST MANAGEMENT</p>

          <h2>Request Status Tracking</h2>

          <p>
            Track the progress of rescue requests from submission
            to delivery.
          </p>
        </div>
      </div>

      {requests.length === 0 ? (
        <div className="empty">
          <Clock size={42} />

          <h3>No requests found</h3>

          <p>
            Rescue teams can create requests from the Rescue
            Requests page.
          </p>
        </div>
      ) : (
        <div className="tracking-list">
          {requests.map(request => (
            <div
              className="tracking-card card"
              key={request.id}
            >
              <div className="tracking-main">

                <div className="tracking-header">
                  <div>
                    <span
                      className={`urgency ${urgencyClass(
                        request.urgency
                      )}`}
                    >
                      {request.urgency}
                    </span>

                    <span className="type">
                      {request.type}
                    </span>
                  </div>

                  <span
                    className={`request-status ${getStatusClass(
                      request.status
                    )}`}
                  >
                    {request.status || "Open"}
                  </span>
                </div>

                <h3>{request.name}</h3>

                <p>
                  <strong>Required:</strong>{" "}
                  {request.quantity} {request.unit}
                </p>

                <p>
                  <strong>Rescue Team:</strong>{" "}
                  {request.team}
                </p>

                <p>
                  <MapPin size={14} />
                  {request.location}
                </p>

                <div className="status-actions">

                  {request.status !== "In Transit" &&
                    request.status !== "Delivered" && (
                      <button
                        className="status-button"
                        onClick={() =>
                          updateRequestStatus(
                            request.id,
                            "In Transit"
                          )
                        }
                      >
                        🚚 Mark In Transit
                      </button>
                    )}

                  {request.status !== "Delivered" && (
                    <button
                      className="status-button delivered-button"
                      onClick={() =>
                        updateRequestStatus(
                          request.id,
                          "Delivered"
                        )
                      }
                    >
                      ✓ Mark Delivered
                    </button>
                  )}

                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
function Stat({ icon, label, value }) {
  return (
    <div className="stat card">
      <div className="stat-icon">{icon}</div>
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

function Step({ n, title, text }) {
  return (
    <div className="step">
      <div className="step-no">{n}</div>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </div>
  );
}

function Category({ icon, name }) {
  return (
    <div className="category">
      <div>{icon}</div>
      <span>{name}</span>
    </div>
  );
}

function FormPage({
  title,
  subtitle,
  onSubmit,
  form,
  setForm,
  button,
  providerLabel,
  providerField
}) {
  const update = (key, value) =>
    setForm({
      ...form,
      [key]: value
    });

  // Get user's current GPS location
  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        setForm({
          ...form,
          latitude: latitude.toFixed(6),
          longitude: longitude.toFixed(6)
        });

        alert("📍 Current location detected successfully!");
      },
      (error) => {
        if (error.code === 1) {
          alert(
            "Location permission was denied. Please allow location access."
          );
        } else if (error.code === 2) {
          alert("Unable to detect your location.");
        } else if (error.code === 3) {
          alert("Location request timed out. Please try again.");
        } else {
          alert("Unable to get your current location.");
        }
      }
    );
  };

  // Convert place name into latitude and longitude
  const findPlaceLocation = async () => {
    const place = form.location?.trim();

    if (!place) {
      alert("Please enter a place name first.");
      return;
    }

    try {
      const url =
        "https://nominatim.openstreetmap.org/search?" +
        new URLSearchParams({
          q: place,
          format: "jsonv2",
          limit: "1",
          countrycodes: "in"
        });

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error("Location search failed");
      }

      const data = await response.json();

      if (data.length === 0) {
        alert(
          "Location not found. Try entering a more specific place name."
        );
        return;
      }

      const result = data[0];

      setForm({
        ...form,
        latitude: Number(result.lat).toFixed(6),
        longitude: Number(result.lon).toFixed(6),
        location: place
      });

      alert(
        `📍 Location found!\nLatitude: ${Number(result.lat).toFixed(
          6
        )}\nLongitude: ${Number(result.lon).toFixed(6)}`
      );
    } catch (error) {
      console.error(error);
      alert(
        "Unable to find the location. Please check your internet connection and try again."
      );
    }
  };

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">DATA ENTRY</p>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>

      <form
        className="form-card card"
        onSubmit={onSubmit}
      >
        <div className="form-grid">

          <label>
            Resource Type
            <select
              value={form.type}
              onChange={e =>
                update("type", e.target.value)
              }
            >
              <option>Food</option>
              <option>Water</option>
              <option>Medicine</option>
              <option>Shelter</option>
              <option>Transport</option>
              <option>Other</option>
            </select>
          </label>

          <label>
            Product / Resource Name
            <input
              required
              value={form.name}
              onChange={e =>
                update("name", e.target.value)
              }
              placeholder="e.g. Rice, Drinking Water"
            />
          </label>

          <label>
            Quantity
            <input
              required
              type="number"
              min="0.1"
              step="0.1"
              value={form.quantity}
              onChange={e =>
                update("quantity", e.target.value)
              }
              placeholder="e.g. 500"
            />
          </label>

          <label>
            Unit
            <select
              value={form.unit}
              onChange={e =>
                update("unit", e.target.value)
              }
            >
              <option>kg</option>
              <option>litres</option>
              <option>packets</option>
              <option>boxes</option>
              <option>units</option>
              <option>people</option>
            </select>
          </label>

          <label>
            Urgency
            <select
              value={form.urgency}
              onChange={e =>
                update("urgency", e.target.value)
              }
            >
              <option>Critical</option>
              <option>High</option>
              <option>Medium</option>
              <option>Low</option>
            </select>
          </label>

          {/* LOCATION */}
          <label className="full">
            Location
            <input
              required
              value={form.location}
              onChange={e =>
                update("location", e.target.value)
              }
              placeholder="e.g. Coimbatore, Tamil Nadu"
            />
          </label>

          {/* LOCATION BUTTONS */}
          <div className="location-button-area full">

            <button
              type="button"
              className="location-button"
              onClick={findPlaceLocation}
            >
              🔍 Find Location
            </button>

            <button
              type="button"
              className="location-button"
              onClick={getCurrentLocation}
            >
              📍 Use My Current Location
            </button>

          </div>

          {/* COORDINATES */}
          <div className="coordinates-box full">

            <div>
              <strong>Latitude:</strong>
              <span>
                {form.latitude || "Not detected"}
              </span>
            </div>

            <div>
              <strong>Longitude:</strong>
              <span>
                {form.longitude || "Not detected"}
              </span>
            </div>

            {form.latitude && form.longitude && (
              <p className="location-success">
                ✓ Location coordinates detected successfully
              </p>
            )}

          </div>

          <label className="full">
            {providerLabel}

            <input
              required
              value={form[providerField] || ""}
              onChange={e =>
                update(
                  providerField,
                  e.target.value
                )
              }
              placeholder={providerLabel}
            />
          </label>

        </div>

        <button
          className="primary"
          type="submit"
        >
          <CheckCircle2 size={18} />
          {button}
        </button>

      </form>
    </section>
  );
}

export default App;
