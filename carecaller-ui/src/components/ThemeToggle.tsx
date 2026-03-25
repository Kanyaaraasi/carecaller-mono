import { Button } from "@/components/ui/button"
import { RiSunLine, RiMoonLine } from "@remixicon/react"
import { useTheme } from "@/components/theme-provider"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  function toggle() {
    if (theme === "dark") setTheme("light")
    else if (theme === "light") setTheme("dark")
    else {
      // system — flip based on current resolved
      const isDark = document.documentElement.classList.contains("dark")
      setTheme(isDark ? "light" : "dark")
    }
  }

  return (
    <Button variant="ghost" size="icon-sm" onClick={toggle} aria-label="Toggle theme">
      <RiSunLine className="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
      <RiMoonLine className="absolute size-4 scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
    </Button>
  )
}
