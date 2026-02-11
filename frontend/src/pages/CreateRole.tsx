import RoleEditor from "../components/RoleEditor";
import { useNavigate } from "react-router-dom";

export default function CreateRole() {
  const navigate = useNavigate();

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Create Role Page</h2>
      <RoleEditor
        onSave={() => {
          alert("Role created!");
          navigate("/"); // Or wherever
        }}
        onCancel={() => navigate("/")}
      />
    </div>
  );
}
