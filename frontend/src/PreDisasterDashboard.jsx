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

      if (
        !response.ok ||
        data.status !== "success"
      ) {

        throw new Error(
          data.message ||
          "SACHET alert assessment failed."
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
            AI PRE-DISASTER PREPAREDNESS
          </p>

          <h2>
            SACHET Disaster Alert Assessment
          </h2>

          <p>
            The AI-assisted preparedness engine
            analyzes official SACHET alerts from
            the National Disaster Management
            Authority (NDMA) to identify active
            disaster alerts for the selected
            district.
          </p>

        </div>

      </div>


      {/* INPUT CARD */}

      <div className="card">

        <h3>
          Check District Alert
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
              Official SACHET alert information
              will be retrieved automatically.
            </small>

          </label>

        </div>


        <button
          className="primary"
          onClick={calculateRisk}
          disabled={loading}
        >

          {loading
            ? "Checking SACHET..."
            : "🔍 Check Current Alert"}

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

          {/* STATUS CARD */}

          <div className="card">

            <p className="eyebrow">
              SACHET ALERT RESULT
            </p>

            <h2>
              {result.district}
            </h2>

            <p>
              Source:{" "}
              <strong>
                {result.source}
              </strong>
            </p>


            {result.sachet.alert_found ? (

              <>

                {/* PUBLIC DISASTER WARNING */}

                {result.sachet.public_alert ? (

                  <>

                    <div className="risk-score">

                      <strong>
                        {result.sachet.sachet_score}
                      </strong>

                      <span>
                        / 100
                      </span>

                    </div>

                    <h3
                      className={getRiskClass(
                        result.sachet.threat_level
                      )}
                    >
                      {result.sachet.threat_level}
                    </h3>

                    <p>
                      ⚠️ <strong>
                        A disaster-related public warning
                        has been identified from the active
                        SACHET alert.
                      </strong>
                    </p>

                    <p>
                      Active SACHET alerts found:{" "}
                      <strong>
                        {result.sachet.alert_count}
                      </strong>
                    </p>

                  </>

                ) : (

                  /* ACTIVE BUT NON-DISASTER ALERT */

                  <>

                    <div className="risk-score">

                      <strong>
                        {result.sachet.sachet_score}
                      </strong>

                      <span>
                        / 100
                      </span>

                    </div>

                    <h3 className="risk-low">
                      NORMAL
                    </h3>

                    <p>
                      🟢 <strong>
                        No disaster-level public warning
                        is currently identified.
                      </strong>
                    </p>

                    <p>
                      An active SACHET alert is available
                      for this district, but it does not
                      meet the application's
                      disaster-warning threshold.
                    </p>

                    <p>
                      Active SACHET alerts found:{" "}
                      <strong>
                        {result.sachet.alert_count}
                      </strong>
                    </p>

                  </>

                )}

              </>

            ) : (

              /* NO ACTIVE ALERT */

              <>

                <div className="risk-score">

                  <strong>
                    0
                  </strong>

                  <span>
                    / 100
                  </span>

                </div>

                <h3 className="risk-low">
                  NO ACTIVE ALERT
                </h3>

                <p>
                  No active matching SACHET alert
                  was found for this district.
                </p>

                <p>
                  Continue monitoring SACHET because
                  alerts can be issued or updated
                  as conditions change.
                </p>

              </>

            )}

          </div>


          {/* ACTIVE ALERT DETAILS */}

          {result.sachet.alert_found &&
            result.sachet.alerts &&
            result.sachet.alerts.length > 0 && (

            <>

              {result.sachet.alerts.map(
                (alert, index) => (

                  <div
                    className="card"
                    key={
                      alert.identifier ||
                      index
                    }
                  >

                    <p className="eyebrow">
                      ACTIVE SACHET ALERT
                    </p>

                    <h3>
                      🚨{" "}
                      {alert.event ||
                        "Disaster Alert"}
                    </h3>


                    <p>
                      <strong>
                        Severity:
                      </strong>{" "}
                      {alert.severity ||
                        "Not specified"}
                    </p>


                    <p>
                      <strong>
                        Urgency:
                      </strong>{" "}
                      {alert.urgency ||
                        "Not specified"}
                    </p>


                    <p>
                      <strong>
                        Certainty:
                      </strong>{" "}
                      {alert.certainty ||
                        "Not specified"}
                    </p>


                    {alert.headline && (

                      <div>

                        <p>
                          <strong>
                            Alert Details:
                          </strong>
                        </p>

                        <p>
                          {alert.headline}
                        </p>

                      </div>

                    )}


                    {alert.area && (

                      <div>

                        <p>
                          <strong>
                            Affected Area:
                          </strong>
                        </p>

                        <p>
                          {alert.area}
                        </p>

                      </div>

                    )}


                    {alert.effective && (

                      <p>
                        <strong>
                          Effective:
                        </strong>{" "}
                        {alert.effective}
                      </p>

                    )}


                    {alert.expires && (

                      <p>
                        <strong>
                          Expires:
                        </strong>{" "}
                        {alert.expires}
                      </p>

                    )}


                    {alert.instruction && (

                      <div>

                        <p>
                          <strong>
                            Official Instruction:
                          </strong>
                        </p>

                        <p>
                          {alert.instruction}
                        </p>

                      </div>

                    )}


                    {alert.sender && (

                      <p>
                        <strong>
                          Alert Sender:
                        </strong>{" "}
                        {alert.sender}
                      </p>

                    )}

                  </div>

                )
              )}

            </>

          )}


          {/* SCORE EXPLANATION */}

          <div className="card">

            <h3>
              📊 SACHET Alert Assessment
            </h3>

            {result.sachet.alert_found ? (

              <>

                <p>
                  Internal Alert Assessment Score:{" "}
                  <strong>
                    {result.sachet.sachet_score}
                  </strong>
                  {" / 100"}
                </p>

                <p>
                  Public Threat Assessment:{" "}
                  <strong>
                    {result.sachet.threat_level}
                  </strong>
                </p>

                <p>
                  <strong>
                    Assessment Reason:
                  </strong>{" "}
                  {result.sachet.threat_reason}
                </p>

                <p>
                  {result.sachet.score_explanation}
                </p>

                <p>
                  This score is an internal,
                  explainable assessment based on
                  the severity, urgency and certainty
                  values contained in the official
                  SACHET alert. It is not a disaster
                  probability or an official NDMA
                  risk score.
                </p>

              </>

            ) : (

              <>

                <p>
                  No active SACHET alert is
                  currently available for the
                  selected district.
                </p>

                <p>
                  Continue monitoring official
                  disaster alerts because the
                  absence of an active alert does
                  not guarantee that a disaster
                  will not occur.
                </p>

              </>

            )}

          </div>


          {/* PREPAREDNESS ACTION */}

          <div className="card">

            <h3>
              🛡️ Preparedness Guidance
            </h3>


            {/* ACTIVE PUBLIC WARNING */}

            {result.sachet.public_alert ? (

              <div>

                <p>
                  🚨 An active SACHET alert has
                  been identified for{" "}
                  <strong>
                    {result.district}
                  </strong>.
                </p>

                <p>
                  Take appropriate preparedness
                  measures according to the
                  official alert and instructions.
                </p>


                {/* HAZARD-SPECIFIC GUIDANCE */}

                {result.sachet.preparedness_guidance &&
                 result.sachet.preparedness_guidance.length > 0 ? (

                  result.sachet.preparedness_guidance.map(
                    (guidance, index) => (

                      <p key={index}>
                        • {guidance}
                      </p>

                    )
                  )

                ) : (

                  <>

                    <p>
                      • Keep essential food and
                      drinking water ready.
                    </p>

                    <p>
                      • Keep medicines and first-aid
                      supplies available.
                    </p>

                    <p>
                      • Keep important documents and
                      emergency contacts accessible.
                    </p>

                    <p>
                      • Follow instructions issued by
                      the relevant authorities.
                    </p>

                    <p>
                      • Continue monitoring official
                      SACHET alerts.
                    </p>

                  </>

                )}

              </div>

            ) : result.sachet.alert_found ? (

              /* ACTIVE NON-DISASTER ALERT */

              <div>

                <p>
                  🟢 <strong>
                    No disaster-level public warning
                    is currently identified.
                  </strong>
                </p>

                <p>
                  An active SACHET alert is currently
                  available for this district, but it
                  does not meet the application's
                  disaster-warning threshold.
                </p>

                <p>
                  Follow the official instructions
                  and continue monitoring SACHET
                  for updates.
                </p>


                {/* HAZARD-SPECIFIC GUIDANCE */}

                {result.sachet.preparedness_guidance &&
                 result.sachet.preparedness_guidance.length > 0 ? (

                  result.sachet.preparedness_guidance.map(
                    (guidance, index) => (

                      <p key={index}>
                        • {guidance}
                      </p>

                    )
                  )

                ) : (

                  <>

                    <p>
                      • Keep basic emergency
                      supplies ready.
                    </p>

                    <p>
                      • Keep emergency contacts
                      available.
                    </p>

                    <p>
                      • Follow instructions issued
                      by the relevant authorities.
                    </p>

                    <p>
                      • Continue monitoring official
                      SACHET alerts.
                    </p>

                  </>

                )}

              </div>

            ) : (

              /* NO ACTIVE ALERT */

              <div>

                <p>
                  🟢 <strong>
                    No disaster-level public warning
                    is currently identified.
                  </strong>
                </p>

                <p>
                  No active matching SACHET alert
                  was found for this district.
                  Continue monitoring SACHET because
                  alerts can be issued or updated
                  as conditions change.
                </p>


                {/* GENERAL PREPAREDNESS GUIDANCE */}

                {result.sachet.preparedness_guidance &&
                 result.sachet.preparedness_guidance.length > 0 ? (

                  result.sachet.preparedness_guidance.map(
                    (guidance, index) => (

                      <p key={index}>
                        • {guidance}
                      </p>

                    )
                  )

                ) : (

                  <>

                    <p>
                      • Keep basic emergency
                      supplies ready.
                    </p>

                    <p>
                      • Keep emergency contacts
                      available.
                    </p>

                    <p>
                      • Follow instructions issued
                      by the relevant authorities.
                    </p>

                    <p>
                      • Continue monitoring official
                      SACHET alerts.
                    </p>

                  </>

                )}

              </div>

            )}

          </div>


          {/* OFFICIAL SOURCE */}

          <div className="card">

            <h3>
              🏛️ Official Alert Source
            </h3>

            <p>
              This assessment uses official
              disaster alerts published through
              SACHET by the National Disaster
              Management Authority (NDMA).
            </p>

            <p>
              The application retrieves the
              alert information and converts
              the alert's severity, urgency and
              certainty into an explainable
              internal alert assessment.
            </p>

            <p>
              The score is a decision-support
              indicator and is not an official
              NDMA risk score or a probability
              that a disaster will occur.
            </p>

          </div>

        </div>

      )}


      {/* OFFICIAL NOTICE */}

      <div className="official-notice">

        <strong>
          Important:
        </strong>

        {" "}
        This AI-assisted preparedness
        assessment is based on active
        official SACHET alerts from NDMA.
        The system does not predict the exact
        occurrence of a disaster, and the
        absence of an alert does not guarantee
        that no disaster will occur.

      </div>

    </section>

  );
}

export default PreDisasterDashboard;