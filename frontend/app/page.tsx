import Link from "next/link";

export default function HomePage() {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h1>Forex AI Platform</h1>
      <p>Mulai dari dashboard untuk trading, backtest, bot ML, dan AI supervisor.</p>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link href="/(dashboard)"><button>Dashboard</button></Link>
        <Link href="/(auth)/login"><button>Login</button></Link>
        <Link href="/(auth)/register"><button>Register</button></Link>
      </div>
    </div>
  );
}
