import React from 'react';
import {BrowserRouter} from "react-router-dom"
import MDMApp from 'swfrontend/MDMApp'
import {localStorageVariableName} from "swfrontend/AppConfigs";
import LoginPage from "swfrontend/LOGIN/LoginPage";
import getRoutes from "./ScreenRouters";
import "./App.css";

const App = () => {
    return (
        localStorage.getItem(localStorageVariableName.authToken) == null ?
            <LoginPage/> :
            <BrowserRouter><MDMApp routes={getRoutes}/></BrowserRouter>
    )
};

export default App;
