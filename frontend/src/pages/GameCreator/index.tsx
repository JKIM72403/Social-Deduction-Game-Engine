import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API } from "../../services/api";
import Step1_BasicInfo from "./Step1_BasicInfo";
import Step2_Roles from "./Step2_Roles";
import Step3_Review from "./Step3_Review";
import "./GameCreator.css";

export type RoleSlot = {
    roleId: number;
    roleName: string;
    count: number;
};

export type GameData = {
    name: string;
    min_players: number;
    max_players: number;
    role_slots: RoleSlot[];
};

export default function GameCreator() {
    const [step, setStep] = useState(1);
    const [gameData, setGameData] = useState<GameData>({
        name: "",
        min_players: 4,
        max_players: 10,
        role_slots: [],
    });
    const navigate = useNavigate();

    const nextStep = () => setStep((s) => s + 1);
    const prevStep = () => setStep((s) => s - 1);

    const saveGame = async () => {
        try {
            // Transform data for backend
            const payload = {
                name: gameData.name,
                min_players: gameData.min_players,
                max_players: gameData.max_players,
                role_slots: gameData.role_slots.map(slot => ({
                    role: slot.roleId,
                    count: slot.count
                }))
            };

            await API.post("/game-templates/", payload);
            alert("Game Created Successfully!");
            navigate("/");
        } catch (e) {
            console.error(e);
            alert("Failed to create game.");
        }
    };

    return (
        <div className="game-creator-container">
            <h1>Create New Game Template</h1>
            <div className="progress-bar">
                <div className={`step ${step >= 1 ? 'active' : ''}`}>1. Basic Info</div>
                <div className={`step ${step >= 2 ? 'active' : ''}`}>2. Roles</div>
                <div className={`step ${step >= 3 ? 'active' : ''}`}>3. Review</div>
            </div>

            <div className="step-content">
                {step === 1 && (
                    <Step1_BasicInfo
                        data={gameData}
                        update={(d) => setGameData({ ...gameData, ...d })}
                        onNext={nextStep}
                    />
                )}
                {step === 2 && (
                    <Step2_Roles
                        data={gameData}
                        update={(d) => setGameData({ ...gameData, ...d })}
                        onNext={nextStep}
                        onBack={prevStep}
                    />
                )}
                {step === 3 && (
                    <Step3_Review
                        data={gameData}
                        onSave={saveGame}
                        onBack={prevStep}
                    />
                )}
            </div>
        </div>
    );
}
