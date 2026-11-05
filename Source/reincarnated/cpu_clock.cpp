#include "cpu_clock.hpp"
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif
namespace reincarnated {
ThreadWorkClock ReadThreadWorkClock()
{
	ThreadWorkClock clock;
#ifdef _WIN32
	FILETIME created, exited, kernel, user;
	if (GetThreadTimes(GetCurrentThread(), &created, &exited, &kernel, &user)) {
		const uint64_t k = (uint64_t(kernel.dwHighDateTime) << 32) | kernel.dwLowDateTime;
		const uint64_t u = (uint64_t(user.dwHighDateTime) << 32) | user.dwLowDateTime;
		clock.ns = (k + u) * 100;
	}
	ULONG64 cycles = 0;
	if (QueryThreadCycleTime(GetCurrentThread(), &cycles)) clock.cycles = cycles;
#endif
	return clock;
}
} // namespace reincarnated
