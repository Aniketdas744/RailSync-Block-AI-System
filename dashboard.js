(function () {
    "use strict";

    /* =========================================================
       RAILSYNC-AI DASHBOARD
       STRICT BACKEND DATA BINDING
       =========================================================

       Rules:
       1. Never invent dashboard values.
       2. Never recursively guess arrays.
       3. Maintenance blocks come ONLY from
          result.maintenance_schedule.
       4. Deferred maintenance comes ONLY from
          result.deferred_maintenance.
       5. Train-section schedule records are NOT maintenance
          blocks.
       6. Disruption delay is NEVER hard-coded.
       7. Missing values display as "—".
       ========================================================= */


    const API_BASE =
        "https://railsync-block-ai-system-6.onrender.com";

    const SESSION_KEY =
        "railsync_staff_session";

    const REQUEST_KEY =
        "railsync_maintenance_requests";


    let logs = [];

    let currentDataset = null;

    let currentOptimization = null;

    let normalOptimization = null;

    let disruptionOptimization = null;


    const $ = id =>
        document.getElementById(id);


    /* =========================================================
       SESSION
       ========================================================= */

    function getSession() {

        try {

            return JSON.parse(
                localStorage.getItem(
                    SESSION_KEY
                ) || "null"
            );

        } catch {

            return null;
        }
    }


    /* =========================================================
       MAINTENANCE REQUEST STORAGE
       ========================================================= */

    function getRequests() {

        try {

            const value =
                JSON.parse(
                    localStorage.getItem(
                        REQUEST_KEY
                    ) || "[]"
                );


            return Array.isArray(value)
                ? value
                : [];

        } catch {

            return [];
        }
    }


    function saveRequests(data) {

        localStorage.setItem(
            REQUEST_KEY,
            JSON.stringify(data)
        );
    }


    /* =========================================================
       GENERAL HELPERS
       ========================================================= */

    function escapeHtml(value) {

        return String(
            value ?? ""
        ).replace(
            /[&<>"']/g,
            char => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char])
        );
    }


    function displayValue(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return "—";
        }


        return String(value);
    }


    function formatTime(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return "—";
        }


        if (
            typeof value === "string" &&
            value.includes(":")
        ) {

            return value;
        }


        const number =
            Number(value);


        if (!Number.isFinite(number)) {

            return String(value);
        }


        const minutes =
            (
                number % 1440 +
                1440
            ) % 1440;


        const hours =
            Math.floor(
                minutes / 60
            );


        const mins =
            minutes % 60;


        return (
            String(hours).padStart(
                2,
                "0"
            ) +
            ":" +
            String(mins).padStart(
                2,
                "0"
            )
        );
    }


    function addLog(message) {

        logs.unshift(
            `${new Date().toLocaleTimeString()} ${message}`
        );


        logs =
            logs.slice(
                0,
                30
            );


        const box =
            $("logs");


        if (!box) {

            return;
        }


        box.innerHTML =
            logs
                .map(
                    item =>
                        `<div class="log-line">${escapeHtml(item)}</div>`
                )
                .join("");
    }


    /* =========================================================
       API REQUEST
       ========================================================= */

    async function apiRequest(
        path,
        options = {}
    ) {

        const response =
            await fetch(
                `${API_BASE}${path}`,
                {
                    ...options,

                    headers: {
                        "Content-Type":
                            "application/json",

                        ...(options.headers || {})
                    }
                }
            );


        let data = null;


        try {

            data =
                await response.json();

        } catch {

            data = null;
        }


        if (!response.ok) {

            const detail =
                data?.detail ||
                data?.message ||
                `HTTP ${response.status}`;


            throw new Error(
                typeof detail === "string"
                    ? detail
                    : JSON.stringify(detail)
            );
        }


        return data;
    }


    const RAILSYNC_API = {

        async getHealth() {

            return apiRequest(
                "/"
            );
        },


        async getDataset() {

            return apiRequest(
                "/api/real-dataset"
            );
        },


        async optimize(payload) {

            return apiRequest(
                "/api/real-optimize",
                {
                    method: "POST",

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );
        }

    };


    /* =========================================================
       BACKEND STATUS
       ========================================================= */

    function showBackendOnline(
        version
    ) {

        if ($("backendDot")) {

            $("backendDot")
                .style
                .background =
                "#2d9b68";
        }


        if ($("backendStatus")) {

            $("backendStatus")
                .textContent =
                `Backend ONLINE • ${displayValue(
                    version
                )}`;
        }
    }


    function showBackendOffline() {

        if ($("backendDot")) {

            $("backendDot")
                .style
                .background =
                "#b23a45";
        }


        if ($("backendStatus")) {

            $("backendStatus")
                .textContent =
                "Backend OFFLINE";
        }
    }


    /* =========================================================
       DATASET NORMALIZATION
       
       Expected real dataset structure:

       {
           status,
           data_mode,
           corridor_id,
           counts,
           data: {
               sections,
               trains,
               demands,
               maintenance_records,
               goods_forecasts,
               corridor_availability
           }
       }
       ========================================================= */

    function normalizeDataset(
        response
    ) {

        const data =
            response?.data;


        if (
            !data ||
            typeof data !== "object"
        ) {

            throw new Error(
                "The real dataset response does not contain data."
            );
        }


        return {

            raw:
                response,

            status:
                response.status,

            data_mode:
                response.data_mode,

            corridor_id:
                response.corridor_id,

            counts:
                response.counts || {},

            sections:
                Array.isArray(
                    data.sections
                )
                    ? data.sections
                    : [],

            trains:
                Array.isArray(
                    data.trains
                )
                    ? data.trains
                    : [],

            demands:
                Array.isArray(
                    data.demands
                )
                    ? data.demands
                    : [],

            maintenance_records:
                Array.isArray(
                    data.maintenance_records
                )
                    ? data.maintenance_records
                    : [],

            goods_forecasts:
                Array.isArray(
                    data.goods_forecasts
                )
                    ? data.goods_forecasts
                    : [],

            corridor_availability:
                Array.isArray(
                    data.corridor_availability
                )
                    ? data.corridor_availability
                    : [],

            planning_horizon:
                data.planning_horizon,

            horizon_minutes:
                data.horizon_minutes
        };
    }


    /* =========================================================
       OPTIMIZATION NORMALIZATION
       
       EXACT BACKEND FIELDS:

       result.metrics
       result.train_schedule
       result.maintenance_schedule
       result.deferred_maintenance
       result.safety
       result.planning_summary
       ========================================================= */

    function normalizeOptimization(
        response
    ) {

        const result =
            response?.result;


        if (
            !result ||
            typeof result !== "object"
        ) {

            throw new Error(
                "The optimization response does not contain result."
            );
        }


        return {

            raw:
                response,

            status:
                response.status,

            data_mode:
                response.data_mode,

            corridor_id:
                response.corridor_id,

            disruption:
                result.disruption ||
                null,

            metrics:
                result.metrics ||
                {},

            solver:
                result.solver,

            objective_value:
                result.objective_value,

            solver_time_seconds:
                result.solver_time_seconds,

            /*
             * IMPORTANT:
             * This contains TRAIN + SECTION records.
             * It is NOT the maintenance block list.
             */
            train_schedule:
                Array.isArray(
                    result.train_schedule
                )
                    ? result.train_schedule
                    : [],

            /*
             * ONLY maintenance blocks.
             */
            maintenance_schedule:
                Array.isArray(
                    result.maintenance_schedule
                )
                    ? result.maintenance_schedule
                    : [],

            /*
             * ONLY deferred maintenance.
             */
            deferred_maintenance:
                Array.isArray(
                    result.deferred_maintenance
                )
                    ? result.deferred_maintenance
                    : [],

            safety:
                result.safety ||
                {},

            planning_summary:
                result.planning_summary ||
                {}
        };
    }


    /* =========================================================
       DATASET COUNTS
       
       These values are read from the actual dataset.
       No values are invented.
       ========================================================= */

    function renderDatasetCounts() {

        if (!currentDataset) {

            return;
        }


        const counts =
            currentDataset.counts ||
            {};


        if ($("countTrains")) {

            $("countTrains")
                .textContent =
                displayValue(
                    counts.trains
                );
        }


        if ($("countSections")) {

            $("countSections")
                .textContent =
                displayValue(
                    counts.sections
                );
        }


        if ($("countDemands")) {

            $("countDemands")
                .textContent =
                displayValue(
                    counts.maintenance_demands
                );
        }


        /*
         * Do not invent a scalar forecast count.
         *
         * If the existing HTML has a forecast count,
         * use the actual number of returned forecast
         * records. Otherwise nothing is added.
         */

        if ($("countForecasts")) {

            $("countForecasts")
                .textContent =
                currentDataset
                    .goods_forecasts
                    .length > 0

                    ? String(
                        currentDataset
                            .goods_forecasts
                            .length
                    )

                    : "—";
        }
    }


    /* =========================================================
       TRAIN DELAY
       ========================================================= */

    function getTrainDelay(
        trainId,
        optimization
    ) {

        if (!optimization) {

            return null;
        }


        const record =
            optimization
                .train_schedule
                .find(
                    item =>
                        String(
                            item.train_id
                        ) ===
                        String(
                            trainId
                        )
                );


        if (!record) {

            return null;
        }


        return record.departure_delay_min;
    }


    /* =========================================================
       TRAIN BOARD
       ========================================================= */

    function renderTrains(
        trains,
        optimization = null
    ) {

        const body =
            $("trainBoardBody");


        if (!body) {

            return;
        }


        if (
            !Array.isArray(trains) ||
            !trains.length
        ) {

            body.innerHTML = `
                <tr>
                    <td colspan="5">
                        No train data available.
                    </td>
                </tr>
            `;


            if ($("trainCountBadge")) {

                $("trainCountBadge")
                    .textContent =
                    "— trains";
            }


            return;
        }


        if ($("trainCountBadge")) {

            $("trainCountBadge")
                .textContent =
                `${trains.length} trains`;
        }


        body.innerHTML =
            trains
                .map(
                    train => {

                        const id =
                            train.train_id;

                        const name =
                            train.name;

                        const direction =
                            train.direction;

                        const departure =
                            train.scheduled_departure_min;

                        const delay =
                            getTrainDelay(
                                id,
                                optimization
                            );


                        const delayText =
                            delay === null ||
                            delay === undefined

                                ? "—"

                                : String(
                                    delay
                                );


                        let status =
                            "—";


                        if (
                            delay !== null &&
                            delay !== undefined
                        ) {

                            status =
                                Number(delay) > 0

                                    ? "DELAYED"

                                    : "ON PLAN";
                        }


                        return `
                            <tr>

                                <td>

                                    <b>
                                        ${escapeHtml(
                                            displayValue(
                                                id
                                            )
                                        )}
                                    </b>

                                    <br>

                                    <small>
                                        ${escapeHtml(
                                            displayValue(
                                                name
                                            )
                                        )}
                                    </small>

                                </td>


                                <td>
                                    ${escapeHtml(
                                        displayValue(
                                            direction
                                        )
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(
                                        formatTime(
                                            departure
                                        )
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(
                                        delayText
                                    )}
                                </td>


                                <td>

                                    <span class="badge ${
                                        status ===
                                        "ON PLAN"

                                            ? "badge-green"

                                            : status ===
                                              "DELAYED"

                                                ? "badge-orange"

                                                : ""
                                    }">

                                        ${escapeHtml(
                                            status
                                        )}

                                    </span>

                                </td>

                            </tr>
                        `;
                    }
                )
                .join("");
    }


    /* =========================================================
       SECTION MAP
       ========================================================= */

    function renderSections(
        sections
    ) {

        const map =
            $("railMap");


        if (!map) {

            return;
        }


        if ($("sectionCount")) {

            $("sectionCount")
                .textContent =
                sections.length
                    ? `${sections.length} sections`
                    : "—";
        }


        if (!sections.length) {

            map.innerHTML = `
                <div class="section-row">
                    No section data available.
                </div>
            `;

            return;
        }


        map.innerHTML =
            sections
                .map(
                    section => {

                        return `
                            <div
                                class="section-row"
                            >

                                <b>
                                    ${escapeHtml(
                                        displayValue(
                                            section.section_id
                                        )
                                    )}
                                </b>


                                <span>
                                    ${escapeHtml(
                                        displayValue(
                                            section.name
                                        )
                                    )}
                                </span>


                                <span>

                                    ${escapeHtml(
                                        displayValue(
                                            section.from_km
                                        )
                                    )}

                                    km →

                                    ${escapeHtml(
                                        displayValue(
                                            section.to_km
                                        )
                                    )}

                                    km

                                </span>


                                <div
                                    class="section-track"
                                ></div>

                            </div>
                        `;
                    }
                )
                .join("");
    }


    /* =========================================================
       DISRUPTION SELECTORS
       ========================================================= */

    function populateSelectors(
        sections,
        trains
    ) {

        const trainSelect =
            $("disruptionTrain");


        if (trainSelect) {

            trainSelect.innerHTML =
                trains
                    .map(
                        train => `

                            <option
                                value="${escapeHtml(
                                    train.train_id
                                )}"
                            >

                                ${escapeHtml(
                                    displayValue(
                                        train.train_id
                                    )
                                )}

                                —

                                ${escapeHtml(
                                    displayValue(
                                        train.name
                                    )
                                )}

                            </option>

                        `
                    )
                    .join("");
        }


        const sectionSelect =
            $("disruptionSection");


        if (sectionSelect) {

            sectionSelect.innerHTML = `

                <option value="">
                    Select section
                </option>

                ${
                    sections
                        .map(
                            section => `

                                <option
                                    value="${escapeHtml(
                                        section.section_id
                                    )}"
                                >

                                    ${escapeHtml(
                                        displayValue(
                                            section.section_id
                                        )
                                    )}

                                </option>

                            `
                        )
                        .join("")
                }

            `;
        }


        if (
            trainSelect &&
            trains.length
        ) {

            trainSelect.value =
                String(
                    trains[0].train_id
                );
        }


        if (
            sectionSelect &&
            sections.length
        ) {

            sectionSelect.value =
                String(
                    sections[0].section_id
                );
        }
    }


    /* =========================================================
       MAINTENANCE BLOCK PLAN
       
       VERY IMPORTANT:

       This function receives ONLY:

       result.maintenance_schedule

       Therefore:
       3 maintenance records = 3 blocks.

       The 29 train-section records are completely
       separate and never enter this function.
       ========================================================= */

    function renderBlocks(
        blocks
    ) {

        const body =
            $("blockPlanBody");


        if (!body) {

            return;
        }


        if (
            !Array.isArray(blocks) ||
            !blocks.length
        ) {

            body.innerHTML = `
                <tr>
                    <td colspan="6">
                        No optimized maintenance blocks.
                    </td>
                </tr>
            `;


            if ($("blockBadge")) {

                $("blockBadge")
                    .textContent =
                    "—";
            }


            return;
        }


        if ($("blockBadge")) {

            $("blockBadge")
                .textContent =
                `${blocks.length} blocks`;
        }


        body.innerHTML =
            blocks
                .map(
                    block => {

                        const safe =
                            block.safe;


                        let safetyText =
                            "—";


                        if (
                            safe === true
                        ) {

                            safetyText =
                                "SAFE";

                        } else if (
                            safe === false
                        ) {

                            safetyText =
                                "CONFLICT";
                        }


                        return `
                            <tr>

                                <td>
                                    ${escapeHtml(
                                        displayValue(
                                            block.demand_id
                                        )
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(
                                        displayValue(
                                            block.department_label ||
                                            block.department
                                        )
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(
                                        displayValue(
                                            block.section_id
                                        )
                                    )}
                                </td>


                                <td>

                                    ${escapeHtml(
                                        formatTime(
                                            block.start_min
                                        )
                                    )}

                                    –

                                    ${escapeHtml(
                                        formatTime(
                                            block.end_min
                                        )
                                    )}

                                </td>


                                <td>
                                    ${escapeHtml(
                                        displayValue(
                                            block.priority_level
                                        )
                                    )}
                                </td>


                                <td>

                                    <span class="badge ${
                                        safe === true
                                            ? "badge-green"
                                            : safe === false
                                                ? "badge-red"
                                                : ""
                                    }">

                                        ${escapeHtml(
                                            safetyText
                                        )}

                                    </span>

                                </td>

                            </tr>
                        `;
                    }
                )
                .join("");
    }


    /* =========================================================
       FORECAST
       ========================================================= */

    function renderForecast(
        data
    ) {

        const box =
            $("forecastList");


        if (!box) {

            return;
        }


        if (
            !Array.isArray(data) ||
            !data.length
        ) {

            box.innerHTML = `
                <div class="mini-row">
                    No forecast data
                </div>
            `;

            return;
        }


        box.innerHTML =
            data
                .map(
                    item => {

                        return `
                            <div
                                class="mini-row"
                                style="display:block"
                            >

                                <div
                                    style="
                                        display:flex;
                                        justify-content:space-between;
                                        gap:8px
                                    "
                                >

                                    <span>
                                        ${escapeHtml(
                                            displayValue(
                                                item.forecast_id
                                            )
                                        )}
                                    </span>


                                    <b>
                                        ${escapeHtml(
                                            displayValue(
                                                item.expected_goods_trains
                                            )
                                        )}
                                    </b>

                                </div>


                                <div
                                    style="
                                        font-size:11px;
                                        color:#82776d;
                                        margin-top:3px
                                    "
                                >

                                    ${escapeHtml(
                                        displayValue(
                                            item.section_id
                                        )
                                    )}

                                    •

                                    ${escapeHtml(
                                        formatTime(
                                            item.start_min
                                        )
                                    )}

                                    –

                                    ${escapeHtml(
                                        formatTime(
                                            item.end_min
                                        )
                                    )}

                                    •

                                    duration

                                    ${escapeHtml(
                                        displayValue(
                                            item.average_train_duration_min
                                        )
                                    )}

                                    min

                                    •

                                    congestion

                                    ${escapeHtml(
                                        displayValue(
                                            item.congestion_level
                                        )
                                    )}

                                </div>


                                <div
                                    style="
                                        font-size:10px;
                                        color:#9a8e84;
                                        margin-top:2px
                                    "
                                >

                                    ${escapeHtml(
                                        displayValue(
                                            item.source
                                        )
                                    )}

                                </div>

                            </div>
                        `;
                    }
                )
                .join("");
    }


    /* =========================================================
       CORRIDOR AVAILABILITY
       ========================================================= */

    function renderAvailability(
        data
    ) {

        const box =
            $("availabilityList");


        if (!box) {

            return;
        }


        if (
            !Array.isArray(data) ||
            !data.length
        ) {

            box.innerHTML = `
                <div class="mini-row">
                    No availability data
                </div>
            `;

            return;
        }


        box.innerHTML =
            data
                .map(
                    item => {

                        let status =
                            "—";


                        if (
                            item.available === true
                        ) {

                            status =
                                "AVAILABLE";

                        } else if (
                            item.available === false
                        ) {

                            status =
                                "UNAVAILABLE";
                        }


                        return `
                            <div
                                class="mini-row"
                                style="display:block"
                            >

                                <div
                                    style="
                                        display:flex;
                                        justify-content:space-between;
                                        gap:8px
                                    "
                                >

                                    <span>
                                        ${escapeHtml(
                                            displayValue(
                                                item.section_id
                                            )
                                        )}
                                    </span>


                                    <b>
                                        ${escapeHtml(
                                            status
                                        )}
                                    </b>

                                </div>


                                <div
                                    style="
                                        font-size:11px;
                                        color:#82776d;
                                        margin-top:3px
                                    "
                                >

                                    ${escapeHtml(
                                        formatTime(
                                            item.start_min
                                        )
                                    )}

                                    –

                                    ${escapeHtml(
                                        formatTime(
                                            item.end_min
                                        )
                                    )}

                                    ${
                                        item.reason
                                            ? ` • ${escapeHtml(
                                                item.reason
                                            )}`
                                            : ""
                                    }

                                </div>

                            </div>
                        `;
                    }
                )
                .join("");
    }


    /* =========================================================
       OPTIMIZATION RENDERING
       ========================================================= */

    function renderOptimization(
        response
    ) {

        const result =
            normalizeOptimization(
                response
            );


        currentOptimization =
            result;


        const metrics =
            result.metrics ||
            {};


        const safety =
            result.safety ||
            {};


        const summary =
            result.planning_summary ||
            {};


        /* -----------------------------------------------------
           PASSENGER DELAY
           ----------------------------------------------------- */

        if ($("kpiPassenger")) {

            $("kpiPassenger")
                .textContent =
                displayValue(
                    metrics.passenger_delay
                );
        }


        /* -----------------------------------------------------
           TOTAL WAITING
           ----------------------------------------------------- */

        if ($("kpiWaiting")) {

            $("kpiWaiting")
                .textContent =
                displayValue(
                    metrics.total_waiting
                );
        }


        /* -----------------------------------------------------
           POSSESSION
           ----------------------------------------------------- */

        if ($("kpiPossession")) {

            $("kpiPossession")
                .textContent =
                displayValue(
                    metrics.possession_duration
                );
        }


        /* -----------------------------------------------------
           SAFETY CONFLICTS
           ----------------------------------------------------- */

        if ($("kpiSafety")) {

            $("kpiSafety")
                .textContent =
                displayValue(
                    safety.conflict_count
                );
        }


        /* -----------------------------------------------------
           SCHEDULED TASKS
           ----------------------------------------------------- */

        if ($("kpiScheduled")) {

            $("kpiScheduled")
                .textContent =
                displayValue(
                    metrics.scheduled_tasks
                );
        }


        /* -----------------------------------------------------
           DEFERRED TASKS
           ----------------------------------------------------- */

        if ($("kpiDeferred")) {

            $("kpiDeferred")
                .textContent =
                displayValue(
                    metrics.deferred_tasks
                );
        }


        /* -----------------------------------------------------
           OPTIMIZATION ENGINE
           ----------------------------------------------------- */

        if ($("engineSolver")) {

            $("engineSolver")
                .textContent =
                displayValue(
                    result.solver
                );
        }


        if ($("engineObjective")) {

            $("engineObjective")
                .textContent =
                displayValue(
                    result.objective_value
                );
        }


        if ($("engineTime")) {

            $("engineTime")
                .textContent =
                displayValue(
                    result.solver_time_seconds
                ) === "—"

                    ? "—"

                    : `${result.solver_time_seconds} s`;
        }


        if ($("engineAI")) {

            $("engineAI")
                .textContent =

                summary
                    .ai_priority_enabled ===
                    undefined

                    ? "—"

                    : summary
                        .ai_priority_enabled
                        ? "Enabled"
                        : "Disabled";
        }


        if ($("engineGoods")) {

            $("engineGoods")
                .textContent =

                summary
                    .goods_forecast_enabled ===
                    undefined

                    ? "—"

                    : summary
                        .goods_forecast_enabled
                        ? "Enabled"
                        : "Disabled";
        }


        if ($("engineState")) {

            $("engineState")
                .textContent =
                displayValue(
                    result.status
                );
        }


        if ($("solverState")) {

            $("solverState")
                .textContent =
                displayValue(
                    result.status
                );
        }


        /* -----------------------------------------------------
           PLAN BADGE
           ----------------------------------------------------- */

        if ($("planBadge")) {

            $("planBadge")
                .textContent =

                safety.safe === true

                    ? "SAFE PLAN"

                    : safety.safe === false

                        ? "SAFETY REVIEW"

                        : "—";
        }


        /* -----------------------------------------------------
           DISRUPTION BADGE
           ----------------------------------------------------- */

        if ($("disruptionBadge")) {

            $("disruptionBadge")
                .textContent =

                result.disruption?.active ===
                    true

                    ? displayValue(
                        result.disruption.level
                    )

                    : "NORMAL";
        }


        /* -----------------------------------------------------
           MAINTENANCE BLOCKS
           
           ONLY maintenance_schedule.
           ----------------------------------------------------- */

        renderBlocks(
            result.maintenance_schedule
        );


        /* -----------------------------------------------------
           TRAIN BOARD
           ----------------------------------------------------- */

        if (currentDataset) {

            renderTrains(
                currentDataset.trains,
                result
            );
        }


        /* -----------------------------------------------------
           GRAPH
           ----------------------------------------------------- */

        if (currentDataset) {

            renderMareyGraph(
                currentDataset.sections,
                result.train_schedule
            );
        }


        /* -----------------------------------------------------
           DISRUPTION MESSAGE
           ----------------------------------------------------- */

        updateScenarioResult(
            result
        );


        /* -----------------------------------------------------
           LOG
           ----------------------------------------------------- */

        addLog(
            `Optimization completed: ${displayValue(
                result.status
            )} | Passenger delay: ${displayValue(
                metrics.passenger_delay
            )} min | Waiting: ${displayValue(
                metrics.total_waiting
            )} min | Possession: ${displayValue(
                metrics.possession_duration
            )} min | Scheduled: ${displayValue(
                metrics.scheduled_tasks
            )} | Deferred: ${displayValue(
                metrics.deferred_tasks
            )}`
        );
    }


    /* =========================================================
       DISRUPTION MESSAGE
       ========================================================= */

    function updateScenarioResult(
        result
    ) {

        const disruption =
            result.disruption;


        const box =
            $("disruptionMessage") ||
            $("disruptionResult");


        if (!box || !disruption) {

            return;
        }


        const active =
            disruption.active === true;


        if (!active) {

            box.textContent =
                "No active disruption.";

            return;
        }


        const sections =
            Array.isArray(
                disruption.affected_section_ids
            )

                ? disruption
                    .affected_section_ids
                    .join(", ")

                : "—";


        box.textContent =
            `Train ${displayValue(
                disruption.train_id
            )} receives +${displayValue(
                disruption.additional_delay_min
            )} min on ${sections}. ` +
            `Level: ${displayValue(
                disruption.level
            )}. ` +
            `Action: ${displayValue(
                disruption.action
            )}. ` +
            `${displayValue(
                disruption.recommended_action
            )}`;
    }


    /* =========================================================
       DISRUPTION BEFORE / AFTER DISPLAY
       ========================================================= */

    function renderBeforeAfter() {

        const before =
            $("beforeDisruptionResult");


        const after =
            $("afterDisruptionResult");


        if (
            !before &&
            !after
        ) {

            return;
        }


        if (normalOptimization) {

            const metrics =
                normalOptimization.metrics;


            if (before) {

                before.innerHTML = `

                    <div>
                        Passenger Delay:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.passenger_delay
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        Total Waiting:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.total_waiting
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        Possession:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.possession_duration
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        Scheduled Tasks:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.scheduled_tasks
                                )
                            )}
                        </b>
                    </div>

                `;
            }
        }


        if (disruptionOptimization) {

            const metrics =
                disruptionOptimization.metrics;


            if (after) {

                after.innerHTML = `

                    <div>
                        Passenger Delay:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.passenger_delay
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        Total Waiting:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.total_waiting
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        Possession:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.possession_duration
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        Scheduled Tasks:
                        <b>
                            ${escapeHtml(
                                displayValue(
                                    metrics.scheduled_tasks
                                )
                            )}
                        </b>
                    </div>

                `;
            }
        }
    }


    /* =========================================================
       SCENARIO COMPARISON
       ========================================================= */

    function metricChange(
        normal,
        disruption
    ) {

        if (
            normal === null ||
            normal === undefined ||
            disruption === null ||
            disruption === undefined
        ) {

            return "—";
        }


        const a =
            Number(normal);


        const b =
            Number(disruption);


        if (
            !Number.isFinite(a) ||
            !Number.isFinite(b)
        ) {

            return "—";
        }


        const change =
            b - a;


        return change > 0
            ? `+${change}`
            : String(change);
    }


    function renderComparison() {

        const body =
            $("comparisonBody");


        if (!body) {

            renderBeforeAfter();

            return;
        }


        if (
            !normalOptimization ||
            !disruptionOptimization
        ) {

            body.innerHTML = `
                <tr>
                    <td colspan="4">
                        Run normal and disruption scenarios to compare them.
                    </td>
                </tr>
            `;


            if ($("deltaLabel")) {

                $("deltaLabel")
                    .textContent =
                    "Waiting for scenarios";
            }


            renderBeforeAfter();

            return;
        }


        const normalMetrics =
            normalOptimization.metrics;


        const disruptionMetrics =
            disruptionOptimization.metrics;


        const rows = [

            [
                "Passenger Delay",
                normalMetrics.passenger_delay,
                disruptionMetrics.passenger_delay
            ],

            [
                "Freight Delay",
                normalMetrics.freight_delay,
                disruptionMetrics.freight_delay
            ],

            [
                "Total Delay",
                normalMetrics.total_delay,
                disruptionMetrics.total_delay
            ],

            [
                "Total Waiting",
                normalMetrics.total_waiting,
                disruptionMetrics.total_waiting
            ],

            [
                "Possession Duration",
                normalMetrics.possession_duration,
                disruptionMetrics.possession_duration
            ],

            [
                "Scheduled Tasks",
                normalMetrics.scheduled_tasks,
                disruptionMetrics.scheduled_tasks
            ],

            [
                "Deferred Tasks",
                normalMetrics.deferred_tasks,
                disruptionMetrics.deferred_tasks
            ]

        ];


        body.innerHTML =
            rows
                .map(
                    ([
                        label,
                        normal,
                        disruption
                    ]) => `

                        <tr>

                            <td>
                                ${escapeHtml(
                                    label
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    displayValue(
                                        normal
                                    )
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    displayValue(
                                        disruption
                                    )
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    metricChange(
                                        normal,
                                        disruption
                                    )
                                )}
                            </td>

                        </tr>

                    `
                )
                .join("");


        if ($("deltaLabel")) {

            $("deltaLabel")
                .textContent =
                "Normal vs disruption";
        }


        renderBeforeAfter();
    }


    /* =========================================================
       MAREY GRAPH
       ========================================================= */

    function renderMareyGraph(
        sections,
        trainSchedule
    ) {

        const canvas =
            $("mareyCanvas") ||
            $("impactGraph");


        if (
            !canvas ||
            !canvas.getContext
        ) {

            return;
        }


        const ctx =
            canvas.getContext(
                "2d"
            );


        const rect =
            canvas.getBoundingClientRect();


        const width =
            Math.max(
                700,
                Math.floor(
                    rect.width ||
                    canvas.width ||
                    1200
                )
            );


        const height =
            430;


        const ratio =
            window.devicePixelRatio ||
            1;


        canvas.width =
            width * ratio;


        canvas.height =
            height * ratio;


        ctx.setTransform(
            ratio,
            0,
            0,
            ratio,
            0,
            0
        );


        ctx.clearRect(
            0,
            0,
            width,
            height
        );


        ctx.fillStyle =
            "#fffdf8";


        ctx.fillRect(
            0,
            0,
            width,
            height
        );


        if (
            !Array.isArray(sections) ||
            !sections.length ||
            !Array.isArray(trainSchedule) ||
            !trainSchedule.length
        ) {

            ctx.fillStyle =
                "#746a62";


            ctx.font =
                "14px Inter, sans-serif";


            ctx.fillText(
                "No optimized train schedule data available.",
                28,
                42
            );


            return;
        }


        const left =
            90;


        const right =
            30;


        const top =
            25;


        const bottom =
            55;


        const plotWidth =
            width -
            left -
            right;


        const plotHeight =
            height -
            top -
            bottom;


        const times =
            trainSchedule
                .flatMap(
                    item => [

                        Number(
                            item.start_min
                        ),

                        Number(
                            item.end_min
                        )

                    ]
                )
                .filter(
                    Number.isFinite
                );


        const distances =
            sections
                .flatMap(
                    section => [

                        Number(
                            section.from_km
                        ),

                        Number(
                            section.to_km
                        )

                    ]
                )
                .filter(
                    Number.isFinite
                );


        if (
            !times.length ||
            !distances.length
        ) {

            ctx.fillStyle =
                "#746a62";


            ctx.font =
                "14px Inter, sans-serif";


            ctx.fillText(
                "Required graph values are not provided by the backend.",
                28,
                42
            );


            return;
        }


        const minTime =
            Math.min(
                ...times
            );


        const maxTime =
            Math.max(
                ...times
            );


        const minDistance =
            Math.min(
                ...distances
            );


        const maxDistance =
            Math.max(
                ...distances
            );


        const timeRange =
            Math.max(
                1,
                maxTime -
                minTime
            );


        const distanceRange =
            Math.max(
                1,
                maxDistance -
                minDistance
            );


        function x(time) {

            return left +
                (
                    (
                        time -
                        minTime
                    ) /
                    timeRange
                ) *
                plotWidth;
        }


        function y(distance) {

            return top +
                (
                    1 -
                    (
                        (
                            distance -
                            minDistance
                        ) /
                        distanceRange
                    )
                ) *
                plotHeight;
        }


        /* -----------------------------------------------------
           GRID
           ----------------------------------------------------- */

        ctx.strokeStyle =
            "#eadfd2";


        ctx.lineWidth =
            1;


        for (
            let i = 0;
            i <= 5;
            i++
        ) {

            const px =
                left +
                (
                    plotWidth *
                    i /
                    5
                );


            ctx.beginPath();

            ctx.moveTo(
                px,
                top
            );

            ctx.lineTo(
                px,
                top +
                plotHeight
            );

            ctx.stroke();
        }


        for (
            let i = 0;
            i <= 5;
            i++
        ) {

            const py =
                top +
                (
                    plotHeight *
                    i /
                    5
                );


            ctx.beginPath();

            ctx.moveTo(
                left,
                py
            );

            ctx.lineTo(
                left +
                plotWidth,
                py
            );

            ctx.stroke();
        }


        /* -----------------------------------------------------
           AXES
           ----------------------------------------------------- */

        ctx.strokeStyle =
            "#7a1f1f";


        ctx.lineWidth =
            1.5;


        ctx.beginPath();

        ctx.moveTo(
            left,
            top
        );

        ctx.lineTo(
            left,
            top +
            plotHeight
        );

        ctx.lineTo(
            left +
            plotWidth,
            top +
            plotHeight
        );

        ctx.stroke();


        /* -----------------------------------------------------
           TIME LABELS
           ----------------------------------------------------- */

        ctx.fillStyle =
            "#59636e";


        ctx.font =
            "11px Inter, sans-serif";


        for (
            let i = 0;
            i <= 5;
            i++
        ) {

            const time =
                minTime +
                (
                    timeRange *
                    i /
                    5
                );


            const px =
                x(time);


            ctx.textAlign =
                "center";


            ctx.fillText(
                formatTime(
                    Math.round(time)
                ),
                px,
                height -
                25
            );
        }


        /* -----------------------------------------------------
           DISTANCE LABELS
           ----------------------------------------------------- */

        for (
            let i = 0;
            i <= 5;
            i++
        ) {

            const distance =
                minDistance +
                (
                    distanceRange *
                    (
                        5 - i
                    ) /
                    5
                );


            const py =
                y(distance);


            ctx.textAlign =
                "right";


            ctx.fillText(
                `${Math.round(
                    distance
                )} km`,
                left - 10,
                py + 4
            );
        }


        /* -----------------------------------------------------
           AXIS TITLES
           ----------------------------------------------------- */

        ctx.textAlign =
            "center";


        ctx.fillStyle =
            "#4a1717";


        ctx.font =
            "700 12px Inter, sans-serif";


        ctx.fillText(
            "Time",
            left +
            plotWidth / 2,
            height - 8
        );


        ctx.save();


        ctx.translate(
            18,
            top +
            plotHeight / 2
        );


        ctx.rotate(
            -Math.PI / 2
        );


        ctx.fillText(
            "Distance",
            0,
            0
        );


        ctx.restore();


        /* -----------------------------------------------------
           SECTION REFERENCE LINES
           ----------------------------------------------------- */

        ctx.strokeStyle =
            "#d6a63d";


        ctx.lineWidth =
            1;


        sections.forEach(
            section => {

                const from =
                    Number(
                        section.from_km
                    );


                const to =
                    Number(
                        section.to_km
                    );


                if (
                    !Number.isFinite(from) ||
                    !Number.isFinite(to)
                ) {

                    return;
                }


                const py =
                    y(
                        (
                            from +
                            to
                        ) / 2
                    );


                ctx.beginPath();

                ctx.moveTo(
                    left,
                    py
                );

                ctx.lineTo(
                    left +
                    plotWidth,
                    py
                );

                ctx.stroke();
            }
        );


        /* -----------------------------------------------------
           ACTUAL TRAIN-SECTION SCHEDULE
           ----------------------------------------------------- */

        trainSchedule.forEach(
            item => {

                const start =
                    Number(
                        item.start_min
                    );


                const end =
                    Number(
                        item.end_min
                    );


                if (
                    !Number.isFinite(start) ||
                    !Number.isFinite(end)
                ) {

                    return;
                }


                const section =
                    sections.find(
                        value =>
                            value.section_id ===
                            item.section_id
                    );


                if (!section) {

                    return;
                }


                const from =
                    Number(
                        section.from_km
                    );


                const to =
                    Number(
                        section.to_km
                    );


                if (
                    !Number.isFinite(from) ||
                    !Number.isFinite(to)
                ) {

                    return;
                }


                const startY =
                    y(from);


                const endY =
                    y(to);


                const startX =
                    x(start);


                const endX =
                    x(end);


                ctx.strokeStyle =

                    item.direction ===
                    "UP"

                        ? "#7a1f1f"

                        : "#e87522";


                ctx.lineWidth =
                    3;


                ctx.beginPath();

                ctx.moveTo(
                    startX,
                    startY
                );

                ctx.lineTo(
                    endX,
                    endY
                );

                ctx.stroke();
            }
        );
    }


    /* =========================================================
       MAINTENANCE REQUESTS
       ========================================================= */

    function renderRequests() {

        const requests =
            getRequests();


        const maintenance =
            $("maintenanceList");


        if (maintenance) {

            if (!requests.length) {

                maintenance.innerHTML = `
                    <div class="request-card">
                        No local maintenance requests yet.
                    </div>
                `;

            } else {

                maintenance.innerHTML =
                    requests
                        .map(
                            request => `

                                <div
                                    class="request-card"
                                >

                                    <header>

                                        <b>
                                            ${escapeHtml(
                                                displayValue(
                                                    request.section_id
                                                )
                                            )}
                                        </b>


                                        <span
                                            class="badge ${
                                                request.status ===
                                                "APPROVED"

                                                    ? "badge-green"

                                                    : request.status ===
                                                      "DEFERRED"

                                                        ? "badge-orange"

                                                        : ""
                                            }"
                                        >

                                            ${escapeHtml(
                                                displayValue(
                                                    request.status
                                                )
                                            )}

                                        </span>

                                    </header>


                                    <p>

                                        ${escapeHtml(
                                            displayValue(
                                                request.department
                                            )
                                        )}

                                        •

                                        ${escapeHtml(
                                            displayValue(
                                                request.duration_min
                                            )
                                        )}
                                        min

                                        •

                                        ${escapeHtml(
                                            displayValue(
                                                request.priority
                                            )
                                        )}

                                    </p>


                                    <p>
                                        ${escapeHtml(
                                            displayValue(
                                                request.reason
                                            )
                                        )}
                                    </p>


                                    <footer>

                                        <span>
                                            ${escapeHtml(
                                                displayValue(
                                                    request.requested_by
                                                )
                                            )}
                                        </span>

                                    </footer>

                                </div>

                            `
                        )
                        .join("");
            }
        }


        const approval =
            $("approvalList");


        if (!approval) {

            return;
        }


        if (!requests.length) {

            approval.innerHTML = `
                <div class="request-card">
                    No approval items.
                </div>
            `;

            return;
        }


        approval.innerHTML =
            requests
                .map(
                    request => `

                        <div
                            class="request-card"
                        >

                            <header>

                                <b>
                                    ${escapeHtml(
                                        displayValue(
                                            request.section_id
                                        )
                                    )}
                                </b>


                                <span
                                    class="badge ${
                                        request.status ===
                                        "APPROVED"

                                            ? "badge-green"

                                            : request.status ===
                                              "DEFERRED"

                                                ? "badge-orange"

                                                : ""
                                    }"
                                >

                                    ${escapeHtml(
                                        displayValue(
                                            request.status
                                        )
                                    )}

                                </span>

                            </header>


                            <p>
                                ${escapeHtml(
                                    displayValue(
                                        request.reason
                                    )
                                )}
                            </p>


                            ${
                                request.status ===
                                "PENDING"

                                    ? `

                                        <footer>

                                            <span>

                                                <button
                                                    class="btn btn-primary btn-sm"
                                                    data-approve="${escapeHtml(
                                                        request.id
                                                    )}"
                                                >
                                                    Approve
                                                </button>


                                                <button
                                                    class="btn btn-outline btn-sm"
                                                    data-defer="${escapeHtml(
                                                        request.id
                                                    )}"
                                                >
                                                    Defer
                                                </button>

                                            </span>

                                        </footer>

                                    `

                                    : ""
                            }

                        </div>

                    `
                )
                .join("");


        document
            .querySelectorAll(
                "[data-approve]"
            )
            .forEach(
                button => {

                    button.onclick =
                        function () {

                            updateRequest(
                                button.dataset
                                    .approve,

                                "APPROVED"
                            );
                        };
                }
            );


        document
            .querySelectorAll(
                "[data-defer]"
            )
            .forEach(
                button => {

                    button.onclick =
                        function () {

                            updateRequest(
                                button.dataset
                                    .defer,

                                "DEFERRED"
                            );
                        };
                }
            );
    }


    function updateRequest(
        id,
        status
    ) {

        const updated =
            getRequests()
                .map(
                    request =>
                        request.id === id

                            ? {
                                ...request,
                                status
                            }

                            : request
                );


        saveRequests(
            updated
        );


        renderRequests();


        addLog(
            `Maintenance request ${id}: ${status}`
        );
    }


    /* =========================================================
       HEALTH CHECK
       ========================================================= */

    async function checkHealth() {

        try {

            const health =
                await RAILSYNC_API
                    .getHealth();


            showBackendOnline(
                health.version ||
                "ONLINE"
            );


            addLog(
                "Backend health check successful."
            );


            return true;

        } catch (error) {

            showBackendOffline();


            addLog(
                "Backend health check failed: " +
                error.message
            );


            return false;
        }
    }


    /* =========================================================
       LOAD DATASET
       ========================================================= */

    async function loadDataset() {

        const response =
            await RAILSYNC_API
                .getDataset();


        console.log(
            "REAL DATASET RESPONSE:",
            response
        );


        currentDataset =
            normalizeDataset(
                response
            );


        console.log(
            "NORMALIZED REAL DATASET:",
            currentDataset
        );


        renderDatasetCounts();


        renderSections(
            currentDataset.sections
        );


        renderTrains(
            currentDataset.trains,
            null
        );


        renderForecast(
            currentDataset.goods_forecasts
        );


        renderAvailability(
            currentDataset.corridor_availability
        );


        populateSelectors(
            currentDataset.sections,
            currentDataset.trains
        );


        addLog(
            `Dataset loaded: ${displayValue(
                currentDataset.counts.trains
            )} trains, ${displayValue(
                currentDataset.counts.sections
            )} sections, ${displayValue(
                currentDataset.counts.maintenance_demands
            )} maintenance demands.`
        );
    }


    /* =========================================================
       NORMAL OPTIMIZATION
       
       IMPORTANT:
       There is NO fixed 35 here.

       Because this is a normal operation scenario,
       disruption is inactive and delay is 0.

       0 here means "no active disruption", not a
       fabricated result.
       ========================================================= */

    async function runOptimization() {

        const button =
            $("optimizeBtn");


        if (button) {

            button.disabled =
                true;


            button.textContent =
                "Optimizing...";
        }


        try {

            const response =
                await RAILSYNC_API
                    .optimize({

                        disruption_active:
                            false,

                        disruption_train_id:
                            null,

                        disruption_section_id:
                            null,

                        disruption_delay_min:
                            0,

                        disruption_reason:
                            "No active disruption"

                    });


            console.log(
                "NORMAL OPTIMIZATION RESPONSE:",
                response
            );


            normalOptimization =
                normalizeOptimization(
                    response
                );


            renderOptimization(
                response
            );


            renderComparison();


        } catch (error) {

            console.error(
                error
            );


            addLog(
                "Optimization failed: " +
                error.message
            );


            alert(
                "Optimization failed: " +
                error.message
            );


        } finally {

            if (button) {

                button.disabled =
                    false;


                button.textContent =
                    "Run Optimization";
            }
        }
    }


    /* =========================================================
       DISRUPTION SIMULATION
       
       Delay comes ONLY from the disruption input.
       
       No fixed 35.
       ========================================================= */

    async function simulateDisruption() {

        const trainId =
            $("disruptionTrain")
                ?.value ||
            null;


        const sectionId =
            $("disruptionSection")
                ?.value ||
            null;


        const delayInput =
            $("disruptionDelay")
                ?.value;


        const delay =
            Number(
                delayInput
            );


        if (!trainId) {

            showDisruptionError(
                "No affected train was selected."
            );

            return;
        }


        if (!sectionId) {

            showDisruptionError(
                "No affected section was selected."
            );

            return;
        }


        if (
            delayInput ===
                null ||
            delayInput ===
                undefined ||
            delayInput === ""
        ) {

            showDisruptionError(
                "Enter a disruption delay."
            );

            return;
        }


        if (
            !Number.isFinite(delay) ||
            delay < 0
        ) {

            showDisruptionError(
                "Enter a valid disruption delay."
            );

            return;
        }


        try {

            const response =
                await RAILSYNC_API
                    .optimize({

                        disruption_active:
                            true,

                        disruption_train_id:
                            trainId,

                        disruption_section_id:
                            sectionId,

                        /*
                         * THIS is the selected
                         * disruption delay.
                         *
                         * It is never fixed.
                         */
                        disruption_delay_min:
                            delay,

                        disruption_reason:
                            `Track obstruction on ${sectionId}`

                    });


            console.log(
                "DISRUPTION OPTIMIZATION RESPONSE:",
                response
            );


            disruptionOptimization =
                normalizeOptimization(
                    response
                );


            renderOptimization(
                response
            );


            renderComparison();


            if ($("disruptionBadge")) {

                $("disruptionBadge")
                    .textContent =
                    displayValue(
                        disruptionOptimization
                            .disruption
                            ?.level
                    );
            }


            addLog(
                `Disruption simulated: ${trainId} +${delay} min on ${sectionId}.`
            );


        } catch (error) {

            console.error(
                error
            );


            showDisruptionError(
                "Simulation failed: " +
                error.message
            );


            addLog(
                "Disruption simulation failed: " +
                error.message
            );
        }
    }


    /* =========================================================
       DISRUPTION ERROR
       ========================================================= */

    function showDisruptionError(
        message
    ) {

        const box =
            $("disruptionMessage") ||
            $("disruptionResult");


        if (!box) {

            return;
        }


        box.textContent =
            message;
    }


    /* =========================================================
       CLEAR DISRUPTION
       ========================================================= */

    async function clearDisruption() {

        disruptionOptimization =
            null;


        if ($("disruptionMessage")) {

            $("disruptionMessage")
                .textContent =
                "";
        }


        if ($("disruptionResult")) {

            $("disruptionResult")
                .classList
                .add(
                    "hidden"
                );
        }


        if ($("disruptionBadge")) {

            $("disruptionBadge")
                .textContent =
                "NORMAL";
        }


        if ($("beforeDisruptionResult")) {

            $("beforeDisruptionResult")
                .innerHTML =
                "";
        }


        if ($("afterDisruptionResult")) {

            $("afterDisruptionResult")
                .innerHTML =
                "";
        }


        addLog(
            "Disruption cleared. Restoring normal optimization scenario."
        );


        await runOptimization();
    }


    /* =========================================================
       REFRESH DASHBOARD
       ========================================================= */

    async function refreshDashboard() {

        try {

            await checkHealth();

            await loadDataset();

            await runOptimization();

            renderRequests();

        } catch (error) {

            console.error(
                error
            );


            addLog(
                "Dashboard refresh failed: " +
                error.message
            );
        }
    }


    /* =========================================================
       INITIALIZATION
       ========================================================= */

    document.addEventListener(
        "DOMContentLoaded",
        async function () {

            const session =
                getSession();


            if (!session) {

                window.location.href =
                    "index.html";

                return;
            }


            /* -------------------------------------------------
               STAFF
               ------------------------------------------------- */

            if ($("staffName")) {

                $("staffName")
                    .textContent =
                    displayValue(
                        session.name
                    );
            }


            if ($("staffRole")) {

                $("staffRole")
                    .textContent =
                    displayValue(
                        session.role
                    );
            }


            if ($("staffAvatar")) {

                const initials =
                    String(
                        session.name ||
                        "Staff"
                    )
                        .split(
                            /\s+/
                        )
                        .map(
                            part =>
                                part[0]
                        )
                        .join("")
                        .slice(
                            0,
                            2
                        )
                        .toUpperCase();


                $("staffAvatar")
                    .textContent =
                    initials;
            }


            /* -------------------------------------------------
               LOGOUT
               ------------------------------------------------- */

            if ($("logoutBtn")) {

                $("logoutBtn").onclick =
                    function () {

                        localStorage
                            .removeItem(
                                SESSION_KEY
                            );


                        window.location.href =
                            "index.html";
                    };
            }


            /* -------------------------------------------------
               REFRESH
               ------------------------------------------------- */

            if ($("refreshBtn")) {

                $("refreshBtn").onclick =
                    refreshDashboard;
            }


            /* -------------------------------------------------
               OPTIMIZATION
               ------------------------------------------------- */

            if ($("optimizeBtn")) {

                $("optimizeBtn").onclick =
                    runOptimization;
            }


            /* -------------------------------------------------
               NEW REQUEST
               ------------------------------------------------- */

            if ($("newRequestBtn")) {

                $("newRequestBtn").onclick =
                    function () {

                        const modal =
                            $("requestModal");


                        if (!modal) {

                            return;
                        }


                        modal.classList
                            .remove(
                                "hidden"
                            );


                        modal.classList
                            .add(
                                "open"
                            );
                    };
            }


            /* -------------------------------------------------
               CLOSE REQUEST
               ------------------------------------------------- */

            if ($("closeRequest")) {

                $("closeRequest").onclick =
                    function () {

                        const modal =
                            $("requestModal");


                        if (!modal) {

                            return;
                        }


                        modal.classList
                            .remove(
                                "open"
                            );


                        modal.classList
                            .add(
                                "hidden"
                            );
                    };
            }


            /* -------------------------------------------------
               MAINTENANCE REQUEST FORM
               ------------------------------------------------- */

            if ($("maintenance-form")) {

                $("maintenance-form").onsubmit =
                    function (event) {

                        event.preventDefault();


                        const request = {

                            id:
                                "REQ-" +
                                Date.now(),

                            section_id:
                                $("request-section")
                                    ?.value
                                    .trim() ||
                                "",

                            department:
                                $("request-department")
                                    ?.value ||
                                "",

                            duration_min:
                                Number(
                                    $("request-duration")
                                        ?.value ||
                                    0
                                ),

                            priority:
                                $("request-priority")
                                    ?.value ||
                                "",

                            reason:
                                $("request-reason")
                                    ?.value
                                    .trim() ||
                                "",

                            status:
                                "PENDING",

                            requested_by:
                                session.name,

                            created_at:
                                new Date()
                                    .toISOString()
                        };


                        if (
                            !request.section_id ||
                            !request.department ||
                            !request.reason
                        ) {

                            if ($("requestError")) {

                                $("requestError")
                                    .textContent =
                                    "Please complete all fields.";
                            }


                            return;
                        }


                        if ($("requestError")) {

                            $("requestError")
                                .textContent =
                                "";
                        }


                        saveRequests([

                            request,

                            ...getRequests()

                        ]);


                        renderRequests();


                        $("maintenance-form")
                            .reset();


                        const modal =
                            $("requestModal");


                        if (modal) {

                            modal.classList
                                .remove(
                                    "open"
                                );


                            modal.classList
                                .add(
                                    "hidden"
                                );
                        }


                        addLog(
                            "New maintenance request submitted."
                        );
                    };
            }


            /* -------------------------------------------------
               DISRUPTION SIMULATION
               
               CORRECT HTML ID:
               simulateDisruptionBtn
               ------------------------------------------------- */

            if ($("simulateDisruptionBtn")) {

                $("simulateDisruptionBtn")
                    .onclick =
                    simulateDisruption;
            }


            /* -------------------------------------------------
               CLEAR DISRUPTION
               ------------------------------------------------- */

            if ($("clearDisruptionBtn")) {

                $("clearDisruptionBtn")
                    .onclick =
                    clearDisruption;
            }


            /* -------------------------------------------------
               GRAPH RESIZE
               ------------------------------------------------- */

            window.addEventListener(
                "resize",
                function () {

                    if (
                        currentOptimization &&
                        currentDataset
                    ) {

                        renderMareyGraph(

                            currentDataset.sections,

                            currentOptimization
                                .train_schedule
                        );
                    }
                }
            );


            /* -------------------------------------------------
               START DASHBOARD
               ------------------------------------------------- */

            await refreshDashboard();

        }
    );

})();
