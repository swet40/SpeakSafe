import React,{ useState,useEffect} from 'react';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { PiMicrophoneLight,PiMicrophoneSlash} from "react-icons/pi";
import SoundLoading from './SoundLoading';
import "./Dictaphone.css"
import { useSocket } from "../AppContext/SocketContext";

const Dictaphone = () => { 
  const {transcript,listening,resetTranscript,browserSupportsSpeechRecognition} = useSpeechRecognition();
  const [totalTranscript,setTotalTranscript]=useState();
  const [initialListening,setInitialLinsteing]=useState(false);
  const [prediction,setPrediction]=useState();
  const socket = useSocket();

  useEffect(() => {
  if (socket) {
    socket.on("prediction", (data) => {
      console.log("Received prediction:", data); 
      console.log("Reason type:", typeof data.reason, "Value:", data.reason); 
      setPrediction(data);
    });


    return () => socket.off("prediction");
  }
}, [socket]);

  useEffect(() => {
    if(!initialListening)
        return;
    if(transcript&&socket){
        console.log(transcript);

        socket.emit("predict", { text: transcript, id: "user1" });

        setTotalTranscript((prev) => { if(prev) return prev + transcript;else  return transcript });
    }
    setTimeout(()=>{
        SpeechRecognition.startListening()
    },500);
  }, [listening,socket]);

  if (!browserSupportsSpeechRecognition) {
    return <span>Browser doesn't support speech recognition.</span>;
  }
  
  const getBackgroundColor = () => {
  const score = prediction?.fraud_probability;
  if (typeof score !== "number") return "bg-gray-100"; 
  if (score < 50) return "greenColor";
  if (score >= 50 && score < 75) return "orangeColor";
  return "redColor";
};

  return (
    <div className="dictaphone-container">
      <div className="dictaphone-card">
        <h2 className="dictaphone-title">🎙️ Speech Recognition</h2>
        <span className={`microphone-status ${listening ? "microphone-on" : "microphone-off"}`}>
          {listening ? "Listening..." : "Microphone Off"}
        </span>

        <button className="dictaphone-reset" onClick={() => { resetTranscript(); setTotalTranscript(""); setPrediction()}} >
          Reset
        </button>

        <div className="dictaphone-transcript">{transcript || "Start speaking..."}</div>
        <div className="dictaphone-transcript-total">{totalTranscript || "Total transcript will appear here..."}</div>
          {typeof prediction?.fraud_probability === "number" && (
            <div className={`dictaphone-transcript  ${getBackgroundColor()}`}>
              <p><strong>Fraud Probability:</strong> <span className='predication-value'>{prediction.fraud_probability}%</span></p>
              <p> <strong>Reason:</strong> {typeof prediction.reason === "string" && prediction.reason.trim() !== "" ? prediction.reason : "No reason provided"}</p>

            </div>

          )}

        {listening && <SoundLoading />}

        <div className="button-container">
          <button onClick={() => { SpeechRecognition.startListening({ continuous: true }); setInitialLinsteing(true) }} 
                  className="microphone-button button-start">
            <PiMicrophoneLight size={30} />
          </button>

          <button onClick={() => { SpeechRecognition.stopListening(); setInitialLinsteing(false) }} 
                  className="microphone-button button-stop">
            <PiMicrophoneSlash size={30} />
          </button>
        </div>
      </div>
    </div>
  );
};
export default Dictaphone;