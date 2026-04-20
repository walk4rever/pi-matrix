export default function DashboardPage() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-6">我的数字员工</h1>
      <div className="grid grid-cols-3 gap-4">
        <Card title="设备状态" href="/dashboard/devices" />
        <Card title="记忆管理" href="/dashboard/memory" />
        <Card title="配置" href="/dashboard/config" />
      </div>
    </main>
  );
}

function Card({ title, href }: { title: string; href: string }) {
  return (
    <a href={href} className="block p-6 border rounded-lg hover:bg-gray-50 transition">
      <h2 className="font-semibold">{title}</h2>
    </a>
  );
}
