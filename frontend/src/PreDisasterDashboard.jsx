import { useState } from "react";

const API =
  import.meta.env.VITE_API_URL || "/api";

function PreDisasterDashboard() {

  const [district, setDistrict] =
    useState("Coimbatore");

  const [result, setResult] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const districts = [
    "Ariyalur",
    "Chengalpattu",
    "Chennai",
    "Coimbatore",
    "Cuddalore",
    "Dharmapuri",
    "Dindigul",
    "Erode",
    "Kallakurichi",
    "Kanchipuram",
    "Kanniyakumari",
    "Karur",
    "Krishnagiri",
    "Madurai",
    "Mayiladuthurai",
    "Nagapattinam",
    "Namakkal",
    "Perambalur",
    "Pudukkottai",
    "Ramanathapuram",
    "Ranipet",
    "Salem",
    "Sivaganga",
    "Tenkasi",
    "Thanjavur",
    "The Nilgiris",
    "Theni",
    "Thoothukudi",
    "Tiruchirappalli",
    "Tirunelveli",
    "Tirupathur",
    "Tiruppur",
    "Tiruvallur",
    "Tiruvannamalai",
    "Tiruvarur",
    "Vellore",
    "Viluppuram",
    "Virudhunagar"
  ];

  const calculateRisk = async () => {

    setLoading(true);
    setResult(null);
    setError("");

    try {

      const params =
        new URLSearchParams({
          district: district
        });

      const response = await fetch(
        `${API}/pre-disaster/risk?${params}`
      );

      const data =
        await response.json();

      if (!response.ok ||
          data.status !== "success") {

        throw new Error(
          data.message ||
          "Risk calculation failed."
        );
      }

      setResult(data);

    } catch (error) {

      setError(
        error.message ||
        "Unable to connect to the backend."
      );

    } finally {

      setLoading(false);

    }
  };

  const getRiskClass = (level) => {

    if (level === "CRITICAL") {
      return "risk-critical";
    }

    if (level === "HIGH") {
      return "risk-high";
    }

    if (level === "MEDIUM") {
      return "risk-medium";
    }

    return "risk-low";
  };

  return (

    <section className="pre-disaster">

      {/* PAGE HEADING */}

      <div className="page-heading">

        <div>

          <p className="eyebrow">
            AI PRE-DISASTER ANALYSIS
          </p>

          <h2>
            IMD + CWC Risk Assessment
          </h2>

          <p>
            The AI-assisted engine analyzes
            official weather warning information
            and CWC historical water-level data
            to calculate an explainable
            preparedness risk score.
          </p>

        </div>

      </div>


      {/* INPUT CARD */}

      <div className="card">

        <h3>
          Risk Assessment
        </h3>

        <div className="form-grid">

          <label>

            Select District

            <select
              value={district}
              onChange={(e) =>
                setDistrict(e.target.value)
              }
            >

              {districts.map((item) => (

                <option
                  key={item}
                  value={item}
                >
                  {item}
                </option>

              ))}

            </select>

            <small>
              IMD and CWC information will
              be retrieved automatically.
            </small>

          </label>

        </div>


        <button
          className="primary"
          onClick={calculateRisk}
          disabled={loading}
        >

          {loading
            ? "Analyzing..."
            : "🔍 Check Current Risk"}

        </button>

      </div>


      {/* ERROR */}

      {error && (

        <div className="card">

          <p>
            ⚠️ <strong>Error:</strong>{" "}
            {error}
          </p>

        </div>

      )}


      {/* RESULTS */}

      {result && (

        <div className="risk-result">


          {/* OVERALL RISK */}

          <div className="card">

            <p className="eyebrow">
              AI RISK RESULT
            </p>

            <h2>
              {result.district}
            </h2>

            <div className="risk-score">

              <strong>
                {result.final_score}
              </strong>

              <span>
                / 100
              </span>

            </div>

            <h3
              className={getRiskClass(
                result.risk_level
              )}
            >
              {result.risk_level}
            </h3>

            <p>
              Overall preparedness risk
              calculated from IMD weather
              warning information and CWC
              historical water-level analysis.
            </p>

          </div>


          {/* IMD + CWC */}

          <div className="two-col">


            {/* IMD */}

            <div className="card">

              <h3>
                🌦️ IMD Weather Analysis
              </h3>

              <p>
                IMD Score:{" "}
                <strong>
                  {result.imd.imd_score}
                </strong>
                {" / 100"}
              </p>

              <p>
                Risk Level:{" "}
                <strong>
                  {result.imd.imd_level}
                </strong>
              </p>

              <p>
                Warning Date:{" "}
                <strong>
                  {result.imd.date}
                </strong>
              </p>

              <p>
                Warning:
              </p>

              {result.imd.warnings &&
                result.imd.warnings.length > 0 ? (

                result.imd.warnings.map(
                  (warning, index) => (

                    <p key={index}>
                      ⚠️ {warning}
                    </p>

                  )
                )

              ) : (

                <p>
                  No specific warning text
                  available.
                </p>

              )}

              <p>
                IMD contributes{" "}
                <strong>60%</strong>
                {" "}of the final score.
              </p>

            </div>


            {/* CWC */}

            <div className="card">

              <h3>
                🌊 CWC Water-Level Analysis
              </h3>

              <p>
                CWC Score:{" "}
                <strong>
                  {result.cwc.cwc_score}
                </strong>
                {" / 100"}
              </p>

              <p>
                Risk Level:{" "}
                <strong>
                  {result.cwc.cwc_level}
                </strong>
              </p>

              <p>
                Station:{" "}
                <strong>
                  {result.cwc.station}
                </strong>
              </p>

              <p>
                River:{" "}
                <strong>
                  {result.cwc.river}
                </strong>
              </p>

              <p>
                Latest Water Level:{" "}
                <strong>
                  {result.cwc.latest_level}
                </strong>
              </p>

              <p>
                Latest Reading:{" "}
                <strong>
                  {result.cwc.latest_time}
                </strong>
              </p>

              <p>
                Historical Average:{" "}
                <strong>
                  {result.cwc.average_level}
                </strong>
              </p>

              <p>
                CWC contributes{" "}
                <strong>40%</strong>
                {" "}of the final score.
              </p>

            </div>

          </div>


          {/* SCORE BREAKDOWN */}

          <div className="card">

            <h3>
              📊 Risk Score Breakdown
            </h3>

            <p>
              IMD Weather Score:
              {" "}
              <strong>
                {result.imd.imd_score}
              </strong>
              {" "}× 60%
            </p>

            <p>
              CWC Water-Level Score:
              {" "}
              <strong>
                {result.cwc.cwc_score}
              </strong>
              {" "}× 40%
            </p>

            <p>
              Final Risk Score:
              {" "}
              <strong>
                {result.final_score}
              </strong>
              {" / 100"}
            </p>

            <p>
              {result.explanation}
            </p>

          </div>


          {/* CWC INFORMATION */}

          <div className="card">

            <h3>
              🌊 CWC Historical Information
            </h3>

            <p>
              The selected district is
              associated with the nearest
              available CWC monitoring station.
            </p>

            <p>
              Monitoring Station:
              {" "}
              <strong>
                {result.cwc.station}
              </strong>
            </p>

            <p>
              Station District:
              {" "}
              <strong>
                {result.cwc.district}
              </strong>
            </p>

            <p>
              River:
              {" "}
              <strong>
                {result.cwc.river}
              </strong>
            </p>

            <p>
              Historical Minimum:
              {" "}
              <strong>
                {result.cwc.minimum_level}
              </strong>
            </p>

            <p>
              Historical 90th Percentile:
              {" "}
              <strong>
                {result.cwc.percentile_90}
              </strong>
            </p>

            <p>
              Historical 95th Percentile:
              {" "}
              <strong>
                {result.cwc.percentile_95}
              </strong>
            </p>

          </div>


          {/* PREPAREDNESS ACTION */}

          <div className="card">

            <h3>
              🛡️ Recommended Preparedness Action
            </h3>


            {result.risk_level ===
              "CRITICAL" && (

              <div>

                <p>
                  🚨 Risk level is CRITICAL.
                </p>

                <p>
                  Prepare essential resources
                  immediately and review
                  emergency response readiness.
                </p>

                <p>
                  • Keep food and drinking water
                  ready.
                </p>

                <p>
                  • Keep essential medicines
                  available.
                </p>

                <p>
                  • Prepare emergency shelter
                  arrangements.
                </p>

                <p>
                  • Closely monitor official
                  emergency announcements.
                </p>

              </div>

            )}


            {result.risk_level ===
              "HIGH" && (

              <div>

                <p>
                  ⚠️ Risk level is HIGH.
                </p>

                <p>
                  Increase preparedness and
                  keep essential resources ready.
                </p>

                <p>
                  • Store drinking water and
                  essential food.
                </p>

                <p>
                  • Keep medicines and first-aid
                  supplies available.
                </p>

                <p>
                  • Monitor official weather
                  updates.
                </p>

              </div>

            )}


            {result.risk_level ===
              "MEDIUM" && (

              <div>

                <p>
                  🟡 Risk level is MEDIUM.
                </p>

                <p>
                  Monitor official updates and
                  prepare essential resources
                  for possible escalation.
                </p>

                <p>
                  • Keep basic food and water
                  available.
                </p>

                <p>
                  • Check emergency contacts.
                </p>

                <p>
                  • Monitor IMD weather warnings.
                </p>

              </div>

            )}


            {result.risk_level ===
              "LOW" && (

              <div>

                <p>
                  🟢 Risk level is LOW.
                </p>

                <p>
                  Continue monitoring official
                  weather and water-level
                  information.
                </p>

                <p>
                  • Keep basic emergency supplies
                  ready.
                </p>

                <p>
                  • Stay aware of official
                  warnings.
                </p>

              </div>

            )}

          </div>

        </div>

      )}


      {/* OFFICIAL NOTICE */}

      <div className="official-notice">

        <strong>
          Important:
        </strong>

        {" "}
        This AI-assisted score is a
        decision-support indicator based
        on official IMD warning information
        and CWC historical water-level data.
        It does not guarantee that a disaster
        will occur.

      </div>

    </section>

  );
}

export default PreDisasterDashboard;