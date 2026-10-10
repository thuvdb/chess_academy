import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Users, UserPlus, Trash2,
  BookOpen, Calendar, GraduationCap, RefreshCw, Search, X
} from 'lucide-react';
import { getClassById, getClassStudents, enrollStudent, unenrollStudent, searchMembers, type ClassItem, type EnrollmentItem, type UserSearchResult } from '../lib/classApi';
import ClassForm from '../components/ClassForm';
import GenerateInvoiceModal from '../components/GenerateInvoiceModal';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const LEVEL_COLORS: Record<string, string> = {
  beginner: 'bg-green-500/15 text-green-400 border border-green-500/30',
  intermediate: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  advanced: 'bg-purple-500/15 text-purple-400 border border-purple-500/30',
  tournament: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
};

function ScheduleDisplay({ schedule }: { schedule: Record<string, string[]> | null }) {
  if (!schedule || Object.keys(schedule).length === 0) {
    return <span className="text-slate-500 text-sm">No schedule set</span>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(schedule).map(([day, times]) =>
        times.map(time => (
          <span key={`${day}-${time}`} className="bg-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded-lg border border-slate-600">
            {day} {time}
          </span>
        ))
      )}
    </div>
  );
}

export default function StudentList() {
  const { classId } = useParams<{ classId: string }>();

  const [cls, setCls] = useState<ClassItem | null>(null);
  const [students, setStudents] = useState<EnrollmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEnroll, setShowEnroll] = useState(false);
  // Student search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<UserSearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const { user } = useAuthStore();

  const fetchAll = useCallback(async () => {
    if (!classId) return;
    setLoading(true);
    try {
      const [clsRes, stuRes] = await Promise.all([
        getClassById(classId),
        getClassStudents(classId),
      ]);
      setCls(clsRes.data);
      setStudents(stuRes.data);
    } catch {
      toast.error('Failed to load class details');
    } finally {
      setLoading(false);
    }
  }, [classId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  // Live search with 300ms debounce
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchMembers(searchQuery);
        setSearchResults(res.data);
        setShowDropdown(true);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelectStudent = (s: UserSearchResult) => {
    setSelectedStudent(s);
    setSearchQuery('');
    setSearchResults([]);
    setShowDropdown(false);
  };

  const handleClearSelected = () => {
    setSelectedStudent(null);
    setSearchQuery('');
  };

  const handleEnroll = async () => {
    if (!classId || !selectedStudent) {
      toast.error('Please search and select a student first');
      return;
    }
    setEnrolling(true);
    try {
      await enrollStudent(classId, selectedStudent.id);
      toast.success(`${selectedStudent.full_name} enrolled successfully!`);
      setSelectedStudent(null);
      setSearchQuery('');
      setShowEnroll(false);
      fetchAll();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail ?? 'Failed to enroll student');
    } finally {
      setEnrolling(false);
    }
  };

  const handleUnenroll = async (enrollment: EnrollmentItem) => {
    if (!classId) return;
    if (!confirm(`Remove ${enrollment.student_name ?? 'this student'} from the class?`)) return;
    try {
      await unenrollStudent(classId, enrollment.student_id);
      toast.success('Student removed from class');
      fetchAll();
    } catch {
      toast.error('Failed to remove student');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 p-8">
        <RefreshCw className="w-6 h-6 animate-spin mr-3" /> Loading...
      </div>
    );
  }

  if (!cls) {
    return (
      <div className="p-8 text-center text-slate-400">
        <p>Class not found.</p>
        <Link to="/classes" className="text-amber-400 hover:underline mt-2 inline-block">Back to Classes</Link>
      </div>
    );
  }

  const fillPercent = Math.min(100, (cls.current_students / cls.max_students) * 100);

  return (
    <div className="p-8">
      {/* Back nav */}
      <Link to="/classes" className="flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-6 transition-colors w-fit">
        <ArrowLeft className="w-4 h-4" /> Back to Classes
      </Link>

      {/* Class Header Card */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-linear-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">{cls.name}</h1>
                {cls.level && (
                  <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${LEVEL_COLORS[cls.level] ?? 'bg-slate-700 text-slate-300'}`}>
                    {cls.level.charAt(0).toUpperCase() + cls.level.slice(1)}
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
              <div className="bg-slate-900/50 rounded-xl p-3">
                <p className="text-slate-400 text-xs mb-1 flex items-center gap-1"><GraduationCap className="w-3.5 h-3.5" /> Teacher</p>
                <p className="text-white text-sm font-medium">{cls.teacher_name ?? 'Unassigned'}</p>
              </div>
              <div className="bg-slate-900/50 rounded-xl p-3">
                <p className="text-slate-400 text-xs mb-1 flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Students</p>
                <div className="flex items-center gap-2">
                  <p className="text-white text-sm font-medium">{cls.current_students}/{cls.max_students}</p>
                  <div className="flex-1 bg-slate-700 rounded-full h-1.5">
                    <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: `${fillPercent}%` }} />
                  </div>
                </div>
              </div>
              <div className="bg-slate-900/50 rounded-xl p-3 col-span-2 md:col-span-1">
                <p className="text-slate-400 text-xs mb-1 flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Schedule</p>
                <ScheduleDisplay schedule={cls.schedule_json} />
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <button
              onClick={() => setShowEditForm(true)}
              className="text-slate-400 hover:text-amber-400 px-4 py-2 rounded-xl border border-slate-700 hover:border-amber-500/50 transition-all text-sm"
            >
              Edit Class
            </button>
            {(user?.role === 'admin' || user?.role === 'center_admin') && (
              <button
                onClick={() => setShowInvoiceModal(true)}
                className="text-blue-400 hover:text-blue-300 px-4 py-2 rounded-xl border border-blue-500/30 hover:border-blue-400/50 bg-blue-500/10 transition-all text-sm"
              >
                Generate Invoices
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Students Section */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Users className="w-4 h-4 text-amber-400" />
            Enrolled Students
            <span className="ml-1 bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded-full">{students.length}</span>
          </h2>
          <button
            onClick={() => setShowEnroll(!showEnroll)}
            className="flex items-center gap-2 text-sm bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold px-3 py-2 rounded-xl transition-all"
          >
            <UserPlus className="w-4 h-4" />
            Add Student
          </button>
        </div>

        {/* Enroll panel — name search */}
        {showEnroll && (
          <div className="px-6 py-4 bg-slate-900/50 border-b border-slate-700">
            <div className="flex items-start gap-3">
              {/* Search input / selected badge */}
              <div className="flex-1 relative" ref={searchRef}>
                {selectedStudent ? (
                  /* Selected student badge */
                  <div className="flex items-center gap-2 bg-amber-500/15 border border-amber-500/40 rounded-xl px-4 py-2">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                      {selectedStudent.full_name.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-amber-300 text-sm font-medium flex-1">{selectedStudent.full_name}</span>
                    <span className="text-slate-400 text-xs">{selectedStudent.email}</span>
                    <button onClick={handleClearSelected} className="text-slate-400 hover:text-white transition-colors ml-1">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  /* Search input */
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    {searching && (
                      <div className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
                    )}
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      placeholder="Search student by name or email..."
                      autoFocus
                      className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-amber-500 transition-colors placeholder-slate-500"
                      onKeyDown={e => e.key === 'Escape' && setShowEnroll(false)}
                    />
                  </div>
                )}

                {/* Dropdown results */}
                {showDropdown && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-xl z-20 overflow-hidden">
                    {searchResults.map(s => (
                      <button
                        key={s.id}
                        onClick={() => handleSelectStudent(s)}
                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-700 transition-colors text-left"
                      >
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                          {s.full_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-white text-sm font-medium">{s.full_name}</p>
                          <p className="text-slate-400 text-xs">{s.email} · {s.role}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                {showDropdown && searchResults.length === 0 && searchQuery.length >= 2 && !searching && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-xl z-20 px-4 py-3 text-slate-400 text-sm">
                    No students found for "{searchQuery}"
                  </div>
                )}
              </div>

              {/* Enroll button */}
              <button
                onClick={handleEnroll}
                disabled={enrolling || !selectedStudent}
                className="flex items-center gap-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-900 font-semibold px-4 py-2 rounded-xl transition-all text-sm shrink-0"
              >
                {enrolling
                  ? <span className="w-3.5 h-3.5 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin" />
                  : <UserPlus className="w-3.5 h-3.5" />}
                Enroll
              </button>
            </div>
          </div>
        )}

        {students.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p>No students enrolled yet</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-6 py-3 text-slate-400 text-xs font-semibold uppercase tracking-wider">#</th>
                <th className="text-left px-6 py-3 text-slate-400 text-xs font-semibold uppercase tracking-wider">Student</th>
                <th className="text-left px-6 py-3 text-slate-400 text-xs font-semibold uppercase tracking-wider">Enrolled</th>
                <th className="text-left px-6 py-3 text-slate-400 text-xs font-semibold uppercase tracking-wider">Status</th>
                <th className="text-right px-6 py-3 text-slate-400 text-xs font-semibold uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {students.map((s, i) => (
                <tr key={s.id} className="hover:bg-slate-700/20 transition-colors">
                  <td className="px-6 py-3 text-slate-500 text-sm">{i + 1}</td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                        {s.student_name?.charAt(0)?.toUpperCase() ?? '?'}
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">{s.student_name ?? 'Unknown'}</p>
                        <p className="text-slate-400 text-xs">{s.student_email ?? s.student_id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-slate-400 text-sm">
                    {new Date(s.enrolled_at).toLocaleDateString('vi-VN')}
                  </td>
                  <td className="px-6 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium border ${s.status === 'active' ? 'bg-green-500/15 text-green-400 border-green-500/30' : 'bg-slate-700 text-slate-400 border-slate-600'}`}>
                      {s.status.charAt(0).toUpperCase() + s.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-right">
                    {s.status === 'active' && (
                      <button
                        onClick={() => handleUnenroll(s)}
                        className="flex items-center gap-1 text-slate-400 hover:text-red-400 text-xs px-2.5 py-1.5 rounded-lg hover:bg-red-500/10 transition-all ml-auto"
                      >
                        <Trash2 className="w-3.5 h-3.5" /> Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit modal */}
      {showEditForm && (
        <ClassForm
          initialData={cls}
          onClose={(refresh) => {
            setShowEditForm(false);
            if (refresh) fetchAll();
          }}
        />
      )}

      {/* Invoice modal */}
      {showInvoiceModal && classId && user?.center_id && (
        <GenerateInvoiceModal
          classId={classId}
          centerId={user.center_id}
          onClose={(refresh) => {
            setShowInvoiceModal(false);
            if (refresh) fetchAll();
          }}
        />
      )}
    </div>
  );
}
