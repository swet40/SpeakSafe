import React, { useContext } from "react";
import { TypeAnimation } from "react-type-animation";
import { FirebaseContext } from "../ContextFol/FirebaseProvider";
import { useNavigate } from "react-router-dom";
import "./HomePage.css";

const HomePage = () => {
  const { logout } = useContext(FirebaseContext);
  const navigate = useNavigate();

  return (
    <div className="homepage">
      <section className="hero">
        <div className="hero-content">
          <h1>AI That Listens. And Knows When It’s a Scam</h1>
          <TypeAnimation
            sequence={[
              "Detect Suspicious Calls...",
              2000,
              "Stay Secure and Informed...",
              2000,
              "SpeakSafe at Your Service!",
              2000,
            ]}
            speed={50}
            wrapper="span"
            repeat={Infinity}
            className="dynamic-text"
          />
          <p>
            Your safety begins with a conversation.
          </p>
          <button className="cta-button" onClick={() => navigate("/detection")}>
            Start
          </button>
        </div>
        <div className="hero-image">
          <img src="/fraud.png" alt="SpeakSafe" />
        </div>
      </section>
    </div>
  );
};

export default HomePage;
