export default function TrackerPage() {
  return (
    <main className="mx-auto max-w-[1600px] space-y-6 px-6 py-10">
      <header className="mb-2">
        <h1 className="text-2xl font-semibold text-paper">Degree Tracker</h1>
        <p className="text-sm text-muted">
          Track your progress and plan your prerequisite chains.
        </p>
      </header>

      {/* Top Dashboard: Global Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-hairline bg-panel p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            Total Credits Earned
          </p>
          <p className="mt-1 text-3xl font-semibold text-paper">4.0</p>
        </div>
        <div className="rounded-2xl border border-hairline bg-panel p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            Total Quality Points
          </p>
          <p className="mt-1 text-3xl font-semibold text-paper">16.00</p>
        </div>
        <div className="rounded-2xl border border-hairline bg-panel p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            CGPA
          </p>
          <p className="mt-1 text-3xl font-semibold text-accent">4.00</p>
        </div>
      </div>

      {/* Split Layout: Checklist (Left) vs. Transcript (Right) */}
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        
        {/* Left Column: Requirements Sidebar (Sticky) */}
        <div className="sticky top-24 space-y-5 rounded-2xl border border-hairline bg-panel p-5 shadow-sm lg:col-span-4 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto custom-scrollbar">
          <h2 className="text-lg font-medium text-paper">Mechanical Engineering B.Sc.</h2>
          
          <div className="space-y-6">
            {/* Category: Preliminary Core */}
            <div>
              <h3 className="mb-2.5 text-xs font-medium uppercase tracking-wider text-muted">
                Preliminary Core
              </h3>
              <div className="space-y-2">
                {/* Completed Course (Dimmed/Strikethrough) */}
                <div className="flex items-center justify-between rounded-lg bg-elevated px-3 py-2 text-sm opacity-50 transition-opacity hover:opacity-100">
                  <span className="font-medium text-paper line-through">MATH 1510</span>
                  <span className="text-xs text-muted">3.0 CH</span>
                </div>
                {/* Uncompleted Course */}
                <div className="flex items-center justify-between rounded-lg border border-hairline bg-transparent px-3 py-2 text-sm">
                  <span className="font-medium text-paper">PHYS 1050</span>
                  <span className="text-xs text-muted">3.0 CH</span>
                </div>
              </div>
            </div>

            {/* Category: Mechanical Core */}
            <div>
              <h3 className="mb-2.5 text-xs font-medium uppercase tracking-wider text-muted">
                Mechanical Core
              </h3>
              <div className="space-y-2">
                {/* In Progress / Planned Course */}
                <div className="flex items-center justify-between rounded-lg border border-hairline bg-transparent px-3 py-2 text-sm">
                  <span className="font-medium text-paper">MECH 2202</span>
                  <span className="text-xs text-muted">4.0 CH</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-hairline bg-transparent px-3 py-2 text-sm">
                  <span className="font-medium text-paper">MECH 2222</span>
                  <span className="text-xs text-muted">4.0 CH</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Chronological Transcript */}
        <div className="space-y-6 lg:col-span-8">
          
          {/* Year Block (e.g., 2026) */}
          <div className="overflow-hidden rounded-2xl border border-hairline bg-panel shadow-sm">
            
            {/* Year Header */}
            <div className="flex items-end justify-between border-b border-hairline bg-elevated px-6 py-4">
              <div>
                <h2 className="text-2xl font-bold text-paper">2026</h2>
                <div className="mt-1 flex gap-4 text-xs font-medium text-muted">
                  <span>Total Courses: 2</span>
                  <span>Total Credits: 4.0</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs font-medium uppercase tracking-wider text-muted">Yearly CGPA</p>
                <p className="text-lg font-semibold text-accent">4.00</p>
              </div>
            </div>

            {/* Term Block: Fall */}
            <div className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-paper">Fall</h3>
                <span className="rounded-full border border-hairline bg-canvas px-3 py-1 text-xs font-medium text-muted shadow-sm">
                  TGPA 0.00
                </span>
              </div>
              
              {/* Course Rows */}
              <div className="space-y-2">
                
                {/* Row: Planned Course */}
                <div className="flex items-center justify-between rounded-xl border border-hairline bg-transparent px-4 py-3 transition-colors hover:bg-elevated/50">
                  <div className="flex flex-1 items-center gap-4">
                    <span className="w-24 font-medium text-paper">CHEM 1126</span>
                    <span className="flex-1 truncate text-sm text-muted">Chemistry 2 Lab</span>
                  </div>
                  <div className="flex items-center gap-4 md:gap-8">
                    <span className="w-12 text-sm text-muted">1.5 CH</span>
                    
                    {/* Grade Dropdown UI */}
                    <div className="relative">
                      <select 
                        className="appearance-none rounded-lg border border-hairline bg-elevated py-1.5 pl-3 pr-8 text-sm text-paper outline-none transition-colors hover:border-muted focus:border-accent"
                        defaultValue="Planned"
                      >
                        <option value="Planned">Planned</option>
                        <option value="IP">IP</option>
                        <option value="A+">A+</option>
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C+">C+</option>
                        <option value="C">C</option>
                        <option value="D">D</option>
                        <option value="F">F</option>
                      </select>
                      {/* Custom dropdown arrow to match styling */}
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-muted">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                    
                    <span className="w-12 text-right text-sm text-muted">—</span>
                  </div>
                </div>

                {/* Row: Planned Course 2 */}
                <div className="flex items-center justify-between rounded-xl border border-hairline bg-transparent px-4 py-3 transition-colors hover:bg-elevated/50">
                  <div className="flex flex-1 items-center gap-4">
                    <span className="w-24 font-medium text-paper">MECH 2202</span>
                    <span className="flex-1 truncate text-sm text-muted">Thermodynamics</span>
                  </div>
                  <div className="flex items-center gap-4 md:gap-8">
                    <span className="w-12 text-sm text-muted">4.0 CH</span>
                    <div className="relative">
                      <select 
                        className="appearance-none rounded-lg border border-hairline bg-elevated py-1.5 pl-3 pr-8 text-sm text-paper outline-none transition-colors hover:border-muted focus:border-accent"
                        defaultValue="Planned"
                      >
                        <option value="Planned">Planned</option>
                        <option value="IP">IP</option>
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-muted">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                    <span className="w-12 text-right text-sm text-muted">—</span>
                  </div>
                </div>

              </div>
            </div>

            {/* Term Block: Winter */}
            <div className="border-t border-hairline p-6">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-paper">Winter</h3>
                <span className="rounded-full border border-hairline bg-canvas px-3 py-1 text-xs font-medium text-muted shadow-sm">
                  TGPA 4.00
                </span>
              </div>
              
              {/* Course Rows */}
              <div className="space-y-2">
                {/* Row: Completed Course */}
                <div className="flex items-center justify-between rounded-xl border border-hairline bg-transparent px-4 py-3 transition-colors hover:bg-elevated/50">
                  <div className="flex flex-1 items-center gap-4">
                    <span className="w-24 font-medium text-paper">MECH 2222</span>
                    <span className="flex-1 truncate text-sm text-muted">Mechanics of Materials</span>
                  </div>
                  <div className="flex items-center gap-4 md:gap-8">
                    <span className="w-12 text-sm text-muted">4.0 CH</span>
                    <div className="relative">
                      <select 
                        className="appearance-none rounded-lg border border-accent/50 bg-elevated py-1.5 pl-3 pr-8 text-sm font-medium text-accent outline-none transition-colors hover:border-accent focus:border-accent"
                        defaultValue="A"
                      >
                        <option value="Planned">Planned</option>
                        <option value="IP">IP</option>
                        <option value="A+">A+</option>
                        <option value="A">A</option>
                        <option value="B">B</option>
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-accent">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                    <span className="w-12 text-right text-sm font-medium text-paper">16.00</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </main>
  );
}