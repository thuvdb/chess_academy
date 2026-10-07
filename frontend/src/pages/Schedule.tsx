import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ChevronLeft, ChevronRight, BookOpen } from 'lucide-react';
import { getClasses, type ClassItem } from '../lib/classApi';
import toast from 'react-hot-toast';

const DAYS_FULL: Record<string, number> = {
  Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0,
};
const HOUR_LABELS = Array.from({ length: 13 }, (_, i) => i + 7); // 07:00 → 19:00

const LEVEL_COLORS: Record<string, string> = {
  beginner: 'bg-green-600/30 border-green-500/50 text-green-300',
  intermediate: 'bg-blue-600/30 border-blue-500/50 text-blue-300',
  advanced: 'bg-purple-600/30 border-purple-500/50 text-purple-300',
  tournament: 'bg-amber-600/30 border-amber-500/50 text-amber-300',
};

interface CalendarEvent {
  cls: ClassItem;
  day: string;
  dayIndex: number;
  hour: number;
  minute: number;
  endTime?: string;
}

function parseEvents(classes: ClassItem[]): CalendarEvent[] {
  const events: CalendarEvent[] = [];
  classes.forEach(cls => {
    if (!cls.schedule_json || !cls.is_active) return;
    Object.entries(cls.schedule_json).forEach(([day, times]) => {
      times.forEach(time => {
        const [start, end] = time.split('-');
        const [hStr, mStr] = start.split(':');
        events.push({
          cls,
          day,
          dayIndex: DAYS_FULL[day] ?? 1,
          hour: parseInt(hStr, 10),
          minute: parseInt(mStr, 10),
          endTime: end || '',
        });
      });
    });
  });
  return events;
}

// Get week dates (Mon–Sun) for a given date
function getWeekDates(base: Date): Date[] {
  const d = new Date(base);
  const day = d.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return Array.from({ length: 7 }, (_, i) => {
    const nd = new Date(d);
    nd.setDate(d.getDate() + i);
    return nd;
  });
}

export default function Schedule() {
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [weekBase, setWeekBase] = useState(new Date());
  const weekDates = getWeekDates(weekBase);
  const events = parseEvents(classes);

  useEffect(() => {
    getClasses({ limit: 100, is_active: true })
      .then(r => setClasses(r.data))
      .catch(() => toast.error('Failed to load schedule'));
  }, []);

  const prevWeek = () => setWeekBase(d => { const nd = new Date(d); nd.setDate(nd.getDate() - 7); return nd; });
  const nextWeek = () => setWeekBase(d => { const nd = new Date(d); nd.setDate(nd.getDate() + 7); return nd; });
  const goToday = () => setWeekBase(new Date());

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const today = new Date();

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Calendar className="w-6 h-6 text-amber-400" />
            Schedule
          </h1>
          <p className="text-slate-400 text-sm mt-1">Weekly class timetable</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={goToday} className="px-3 py-2 text-sm text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition-all">
            Today
          </button>
          <div className="flex items-center gap-1 bg-slate-800 border border-slate-700 rounded-xl">
            <button onClick={prevWeek} className="p-2 text-slate-400 hover:text-white transition-colors">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-slate-300 text-sm px-2 whitespace-nowrap">
              {weekDates[0].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} –{' '}
              {weekDates[6].toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
            <button onClick={nextWeek} className="p-2 text-slate-400 hover:text-white transition-colors">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* No-schedule prompt */}
      {classes.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">No active classes found</p>
          <Link to="/classes" className="text-amber-400 hover:underline text-sm mt-2 inline-block">Go to Classes →</Link>
        </div>
      )}

      {/* Calendar Grid */}
      {classes.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden">
          {/* Day headers */}
          <div className="grid grid-cols-[64px_repeat(7,1fr)] border-b border-slate-700">
            <div className="px-2 py-3" />
            {dayNames.map((dn, i) => {
              const date = weekDates[i];
              const isToday = date.toDateString() === today.toDateString();
              return (
                <div key={dn} className={`text-center py-3 border-l border-slate-700 ${isToday ? 'bg-amber-500/10' : ''}`}>
                  <p className={`text-xs font-semibold ${isToday ? 'text-amber-400' : 'text-slate-400'}`}>{dn}</p>
                  <p className={`text-lg font-bold mt-0.5 ${isToday ? 'text-amber-400' : 'text-white'}`}>
                    {date.getDate()}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Time rows */}
          <div className="overflow-y-auto max-h-[60vh]">
            {HOUR_LABELS.map(hour => (
              <div key={hour} className="grid grid-cols-[64px_repeat(7,1fr)] border-b border-slate-700/40 min-h-16">
                <div className="px-2 py-2 text-slate-500 text-xs text-right pr-3 pt-2 shrink-0">
                  {hour.toString().padStart(2, '0')}:00
                </div>
                {dayNames.map((dn, di) => {
                  const date = weekDates[di];
                  const isToday = date.toDateString() === today.toDateString();
                  const dayEvents = events.filter(e => e.day === dn && e.hour === hour);
                  return (
                    <div key={dn} className={`border-l border-slate-700/40 p-1 ${isToday ? 'bg-amber-500/5' : ''}`}>
                      {dayEvents.map((ev, ei) => (
                        <Link
                          key={ei}
                          to={`/classes/${ev.cls.id}`}
                          className={`block rounded-lg border px-2 py-1.5 mb-1 text-xs font-medium hover:brightness-125 transition-all ${LEVEL_COLORS[ev.cls.level ?? ''] ?? 'bg-slate-700 border-slate-600 text-slate-300'}`}
                        >
                          <p className="font-semibold truncate">{ev.cls.name}</p>
                          <p className="opacity-75 flex items-center gap-1 mt-0.5">
                            <BookOpen className="w-2.5 h-2.5" />
                            {`${ev.hour.toString().padStart(2, '0')}:${ev.minute.toString().padStart(2, '0')}`}
                            {ev.endTime ? ` - ${ev.endTime}` : ''}
                          </p>
                        </Link>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 flex-wrap">
        {Object.entries(LEVEL_COLORS).map(([lvl, cls]) => (
          <div key={lvl} className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${cls}`}>
            <span className="font-medium capitalize">{lvl}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
