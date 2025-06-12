import React, { useContext } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
  Link,
} from "react-router-dom";

import { FirebaseContext } from "./ContextFol/FirebaseProvider";
import Signup from "./ComponentsFol/Signup";
import Login from "./ComponentsFol/Login";
import HomePage from "./ComponentsFol/HomePage";
import Navbar from "./ComponentsFol/Navbar";
import DetectionOptions from "./ComponentsFol/DetectionOptions";
import Dictaphone from "./Components/Dictaphone"
import { SocketProvider } from "./AppContext/SocketContext";
import Audiofile from "./Components/Audiofile";

const App = () => {
  const { user, logout } = useContext(FirebaseContext);

  return (
    <>
      <Navbar />
      <Router>
        {/* <nav>
        {user ? (
          <Navbar />
        ) : (
          <div>
            <Link to="/signup">Signup</Link>
            <Link to="/login">Login</Link>
          </div>
        )}
      </nav> */}
        <Routes>
          <Route path="/signup" element={<Signup />} />
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<HomePage />} />
          <Route path="/detection" element={<DetectionOptions />} />
          <Route path="/upload-audio" element={<SocketProvider><Audiofile></Audiofile></SocketProvider>} />
          <Route path="/live-detection" element={<SocketProvider><Dictaphone></Dictaphone></SocketProvider>}></Route>
        </Routes>
      </Router>
    </>
  );
};

export default App;