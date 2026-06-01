import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Listings from "./pages/Listings";
import Predict from "./pages/Predict";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Listings />} />
        <Route path="/predict" element={<Predict />} />
        <Route path="*" element={<Listings />} />
      </Route>
    </Routes>
  );
}
