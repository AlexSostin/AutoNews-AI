'use client';

import { useLocaleUnits, kmToMiles, kmhToMph } from '@/hooks/useLocaleUnits';
import UnitToggle from './UnitToggle';

// Must match the type in the parent page
interface VehicleSpecItem {
    id: number;
    trim_name: string;
    make: string;
    model_name: string;
    drivetrain: string | null;
    motor_count: number | null;
    motor_placement: string | null;
    power_hp: number | null;
    power_kw: number | null;
    power_display: string | null;
    torque_nm: number | null;
    acceleration_0_100: number | null;
    top_speed_kmh: number | null;
    battery_kwh: number | null;
    range_km: number | null;
    range_wltp: number | null;
    range_epa: number | null;
    range_cltc: number | null;
    combined_range_km: number | null;
    range_display: string | null;
    charging_time_fast: string | null;
    charging_time_slow: string | null;
    charging_power_max_kw: number | null;
    transmission: string | null;
    body_type: string | null;
    fuel_type: string | null;
    seats: number | null;
    length_mm: number | null;
    width_mm: number | null;
    height_mm: number | null;
    wheelbase_mm: number | null;
    weight_kg: number | null;
    cargo_liters: number | null;
    cargo_liters_max: number | null;
    ground_clearance_mm: number | null;
    towing_capacity_kg: number | null;
    price_from: number | null;
    price_to: number | null;
    currency: string | null;
    price_usd_from: number | null;
    price_usd_to: number | null;
    price_updated_at: string | null;
    price_display: string | null;
    year: number | null;
    country_of_origin: string | null;
    platform: string | null;
    voltage_architecture: number | null;
    suspension_type: string | null;
    [key: string]: any;
}

interface VehicleSpecsTableProps {
    vehicleSpecsList: VehicleSpecItem[];
}

type SpecDef = { label: string; key: string; format: (v: VehicleSpecItem) => string };

export default function VehicleSpecsTable({ vehicleSpecsList }: VehicleSpecsTableProps) {
    const { system, formatDistance, formatSpeed, ready } = useLocaleUnits();

    if (!vehicleSpecsList || vehicleSpecsList.length === 0) return null;

    const vsList = vehicleSpecsList;
    const multi = vsList.length > 1;

    // Locale-aware formatters
    const fmtDist = (v: number | null): string => {
        if (!v) return '';
        return formatDistance(v);
    };

    const fmtSpd = (v: number | null): string => {
        if (!v) return '';
        return formatSpeed(v);
    };

    const fmtNum = (v: number | null, unit: string) => v ? `${v} ${unit}` : '';
    const fmtStr = (v: string | null) => v || '';

    const accelLabel = system === 'imperial' ? '0-60 mph' : '0-100 km/h';

    const evRows: SpecDef[] = [
        { label: 'Battery', key: 'battery_kwh', format: v => fmtNum(v.battery_kwh, 'kWh') },
        { label: 'Range (WLTP)', key: 'range_wltp', format: v => fmtDist(v.range_wltp) },
        { label: 'Range (EPA)', key: 'range_epa', format: v => fmtDist(v.range_epa) },
        { label: 'Range (CLTC)', key: 'range_cltc', format: v => fmtDist(v.range_cltc) },
        {
            label: 'Combined Range', key: 'combined_range_km', format: v => {
                if (!v.combined_range_km) return '';
                const dist = formatDistance(v.combined_range_km);
                return `${dist} (gas+electric)`;
            }
        },
        { label: 'Fast Charging', key: 'charging_time_fast', format: v => fmtStr(v.charging_time_fast) },
        { label: 'Max Charge Power', key: 'charging_power_max_kw', format: v => fmtNum(v.charging_power_max_kw, 'kW') },
        { label: 'Voltage', key: 'voltage_architecture', format: v => v.voltage_architecture ? `${v.voltage_architecture}V` : '' },
    ];

    const perfRows: SpecDef[] = [
        { label: 'Power', key: 'power_display', format: v => fmtStr(v.power_display) },
        { label: 'Torque', key: 'torque_nm', format: v => fmtNum(v.torque_nm, 'Nm') },
        { label: accelLabel, key: 'acceleration_0_100', format: v => v.acceleration_0_100 ? `${v.acceleration_0_100}s` : '' },
        { label: 'Top Speed', key: 'top_speed_kmh', format: v => fmtSpd(v.top_speed_kmh) },
        { label: 'Drivetrain', key: 'drivetrain', format: v => fmtStr(v.drivetrain) },
        { label: 'Motors', key: 'motor_count', format: v => v.motor_count ? `${v.motor_count} (${v.motor_placement || '—'})` : '' },
    ];

    const dimRows: SpecDef[] = [
        { label: 'Length', key: 'length_mm', format: v => fmtNum(v.length_mm, 'mm') },
        { label: 'Width', key: 'width_mm', format: v => fmtNum(v.width_mm, 'mm') },
        { label: 'Height', key: 'height_mm', format: v => fmtNum(v.height_mm, 'mm') },
        { label: 'Wheelbase', key: 'wheelbase_mm', format: v => fmtNum(v.wheelbase_mm, 'mm') },
        {
            label: 'Weight', key: 'weight_kg', format: v => {
                if (!v.weight_kg) return '';
                if (system === 'imperial') return `${Math.round(v.weight_kg * 2.20462).toLocaleString()} lbs`;
                return `${v.weight_kg.toLocaleString()} kg`;
            }
        },
        { label: 'Cargo', key: 'cargo_liters', format: v => fmtNum(v.cargo_liters, 'L') },
        { label: 'Max Cargo', key: 'cargo_liters_max', format: v => fmtNum(v.cargo_liters_max, 'L') },
        { label: 'Ground Clearance', key: 'ground_clearance_mm', format: v => fmtNum(v.ground_clearance_mm, 'mm') },
        {
            label: 'Towing', key: 'towing_capacity_kg', format: v => {
                if (!v.towing_capacity_kg) return '';
                if (system === 'imperial') return `${Math.round(v.towing_capacity_kg * 2.20462).toLocaleString()} lbs`;
                return `${v.towing_capacity_kg.toLocaleString()} kg`;
            }
        },
    ];

    const techRows: SpecDef[] = [
        { label: 'Platform', key: 'platform', format: v => fmtStr(v.platform) },
        { label: 'Transmission', key: 'transmission', format: v => fmtStr(v.transmission) },
        { label: 'Suspension', key: 'suspension_type', format: v => fmtStr(v.suspension_type) },
        { label: 'Body Type', key: 'body_type', format: v => fmtStr(v.body_type) },
        { label: 'Seats', key: 'seats', format: v => v.seats ? `${v.seats}` : '' },
        { label: 'Country', key: 'country_of_origin', format: v => fmtStr(v.country_of_origin) },
    ];

    // Filter rows with at least one non-empty value
    const hasData = (rows: SpecDef[]) => rows.filter(r =>
        vsList.some(vs => { const val = r.format(vs); return val && val !== ''; })
    );

    // Render a section
    const renderSection = (title: string, emoji: string, gradient: string, rows: SpecDef[], showToggle: boolean = false) => {
        const activeRows = hasData(rows);
        if (activeRows.length === 0) return null;
        return (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                <div className={`px-6 py-4 ${gradient}`}>
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-white">{emoji} {title}</h2>
                            {multi && (
                                <p className="text-white/70 text-sm mt-1">
                                    Comparing {vsList.length} trim variants
                                </p>
                            )}
                        </div>
                        {showToggle && ready && (
                            <UnitToggle className="bg-white/20 backdrop-blur-sm" />
                        )}
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        {multi && (
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="text-left px-6 py-3 font-semibold text-gray-500 w-40"></th>
                                    {vsList.map(vs => (
                                        <th key={vs.id} className="text-center px-4 py-3 font-bold text-indigo-700">
                                            {vs.trim_name}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                        )}
                        <tbody>
                            {activeRows.map((row, i) => (
                                <tr key={row.key} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                                    <td className="px-6 py-2.5 font-medium text-gray-600 whitespace-nowrap">{row.label}</td>
                                    {multi ? (
                                        vsList.map(vs => {
                                            const val = row.format(vs);
                                            return (
                                                <td key={vs.id} className="px-4 py-2.5 text-center text-gray-900 font-medium">
                                                    {val || <span className="text-gray-300">—</span>}
                                                </td>
                                            );
                                        })
                                    ) : (
                                        <td className="px-6 py-2.5 text-gray-900 font-medium">
                                            {row.format(vsList[0]) || <span className="text-gray-300">—</span>}
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    return (
        <>
            {renderSection('Performance', '⚡', 'bg-gradient-to-r from-indigo-600 to-purple-600', perfRows, true)}
            {renderSection('EV & Battery', '🔋', 'bg-gradient-to-r from-green-600 to-emerald-600', evRows, true)}
            {renderSection('Dimensions & Weight', '📐', 'bg-gradient-to-r from-cyan-600 to-teal-600', dimRows, true)}
            {renderSection('Technical Details', '🔧', 'bg-gradient-to-r from-orange-500 to-amber-500', techRows)}
        </>
    );
}
