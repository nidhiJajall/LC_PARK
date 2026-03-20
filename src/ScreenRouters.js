import React from "react";
import {Route, Switch} from "react-router-dom";
import LCDetail from "../LC/Screens/LCDetail/LCDetail";
import LCRequest from "../LC/Screens/LCRequest/LCRequest";
// import CapexForm from './capex/CapexForm'
// import CapexList from './capex/CapexList'
export const app = `${process.env.REACT_APP_PROJECT_ROUTE}`;
/**
 * Custom component mapping
 * @param {component} : Component being mapped
 * @param {routers} : Creating route for a component specified with route link
 */
function getRoutes() {
    return ({
        lc_request: {
            component: LCDetail,
            routers: [
                <Switch>
                    {/* List screen */}
                    <Route exact path={`${app}/lc_request`}        component={LCDetail} />
                    {/* Create new */}
                    <Route exact path={`${app}/lc_request/new`}    component={LCRequest} />
                    {/* View / Edit existing by ID */}
                    <Route exact path={`${app}/lc_request/:id`}    component={LCRequest} />
                </Switch>
            ],
        },
        // "CapexForm": {
        //     component: CapexForm,
        //     routers: [<Route path="/app/CapexForm/" component={CapexForm}/>],
        // },
        // "CapexList": {
        //     component: CapexList,
        //     routers: [<Route path="/app/CapexList/" component={CapexList}/>],
        // }
    })
}

export default getRoutes;