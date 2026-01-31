import { useEffect, useState } from "react";
import { API } from "../services/api";

export default function CreateRole() {
  const [abilities, setAbilities] = useState<any[]>([]);
  const [role, setRole] = useState({
    name: "",
    alignment: "TOWN",
    description: "",
    abilities: [] as number[],
  });

  useEffect(() => {
    API.get("/abilities/").then(res => setAbilities(res.data));
  }, []);

  const submit = async () => {
    await API.post("/roles/", role);
    alert("Role created!");
  };

  return (
    <div>
      <h2>Create Role</h2>

      <input
        placeholder="Role Name"
        onChange={e => setRole({ ...role, name: e.target.value })}
      />

      <select onChange={e => setRole({ ...role, alignment: e.target.value })}>
        <option value="TOWN">Town</option>
        <option value="MAFIA">Mafia</option>
        <option value="NEUTRAL">Neutral</option>
      </select>

      <textarea
        placeholder="Description"
        onChange={e => setRole({ ...role, description: e.target.value })}
      />

      <h4>Abilities</h4>
      {abilities.map(a => (
        <label key={a.id}>
          <input
            type="checkbox"
            value={a.id}
            onChange={e => {
              const id = Number(e.target.value);
              setRole(r => ({
                ...r,
                abilities: e.target.checked
                  ? [...r.abilities, id]
                  : r.abilities.filter(x => x !== id),
              }));
            }}
          />
          {a.name}
        </label>
      ))}

      <button onClick={submit}>Save Role</button>
    </div>
  );
}
