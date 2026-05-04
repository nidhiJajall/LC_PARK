import React from "react";
import { Route, Switch } from "react-router-dom";
import LCList from "../LC/Screens/LCDetail/LCList";
import LCRequest from "../LC/Screens/LCRequest/LCRequest";

export const app = `${process.env.REACT_APP_PROJECT_ROUTE=='/null'?"":process.env.REACT_APP_PROJECT_ROUTE}`;

/**
 * Custom component mapping
 * @param {component} : Component being mapped
 * @param {routers}   : Creating route for a component specified with route link
 */
function getRoutes() {
    return ({
        lc_request: {
            component: LCList,
            routers: [
                <Switch>
                    {/* List screen */}
                    <Route exact path={`${app}/lc_request`}     component={LCList} />
                    {/* Create new */}
                    <Route exact path={`${app}/lc_request/new`} component={LCRequest} />
                    {/* View / Edit existing by ID */}
                    <Route exact path={`${app}/lc_request/:id`} component={LCRequest} />
                </Switch>
            ],
        },
    });
}

export default getRoutes;